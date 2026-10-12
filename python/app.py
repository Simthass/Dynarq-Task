"""Owner's page. Run from python/: python app.py."""

import os
import secrets
import sys
import threading
from dataclasses import dataclass
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from plan import build_plan, parse_date, read_json
from views import render_page


@dataclass(frozen=True)
class Config:
    port: int
    data_dir: Path
    today: str

    @classmethod
    def from_env(cls, environment=None):
        env = os.environ if environment is None else environment

        try:
            port = int(env.get("PORT", "8000"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "PORT must be an integer between 1 and 65535"
            ) from exc

        if not 1 <= port <= 65535:
            raise ValueError("PORT must be an integer between 1 and 65535")

        today = env.get("TODAY", date.today().isoformat())
        try:
            parse_date(today)
        except ValueError as exc:
            raise ValueError(
                "TODAY must be a real date in YYYY-MM-DD format"
            ) from exc

        return cls(
            port=port,
            data_dir=Path(env.get("DATA_DIR", "../data")),
            today=today,
        )


def load_plan(config):
    invoices = read_json(config.data_dir / "invoices.json")
    sent = read_json(config.data_dir / "sent.json")
    return invoices, build_plan(invoices, sent, config.today)


def create_server(config):
    # Each running server owns its decisions.
    # The key distinguishes today's invoice and reminder step.
    decisions = {}
    decision_lock = threading.Lock()
    csrf_token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def send_page(self, body, status=200):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if urlsplit(self.path).path != "/":
                self.send_error(404)
                return

            try:
                invoices, plan = load_plan(config)

                with decision_lock:
                    snapshot = decisions.copy()

                self.send_page(render_page(
                    config.today,
                    invoices,
                    plan,
                    decisions=snapshot,
                    csrf_token=csrf_token,
                ))
            except ValueError as exc:
                self.send_page(
                    render_page(config.today, error=str(exc)),
                    503,
                )

        def do_POST(self):
            if urlsplit(self.path).path != "/decision":
                self.send_error(404)
                return

            content_type = (
                self.headers.get("Content-Type", "")
                .split(";")[0]
                .strip()
                .lower()
            )
            if content_type != "application/x-www-form-urlencoded":
                self.send_error(415, "Use a form to submit a decision")
                return

            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self.send_error(400, "Invalid request length")
                return

            if not 0 < length <= 8192:
                self.send_error(
                    400,
                    "Decision form must be between 1 and 8192 bytes",
                )
                return

            try:
                fields = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=4,
                )
            except (ValueError, UnicodeError):
                self.send_error(400, "Invalid decision form")
                return

            expected = {"invoice_id", "step", "decision", "csrf_token"}
            if set(fields) != expected or any(
                len(values) != 1 for values in fields.values()
            ):
                self.send_error(
                    400,
                    "Decision form has missing or repeated fields",
                )
                return

            form = {
                key: values[0]
                for key, values in fields.items()
            }

            if not secrets.compare_digest(
                form["csrf_token"].encode("utf-8"),
                csrf_token.encode("ascii"),
            ):
                self.send_error(
                    403,
                    "Reload the page before submitting a decision",
                )
                return

            if form["decision"] not in ("approved", "rejected"):
                self.send_error(
                    400,
                    "Decision must be approved or rejected",
                )
                return

            # Recheck the current plan rather than trusting submitted fields.
            try:
                _, plan = load_plan(config)
            except ValueError as exc:
                self.send_page(
                    render_page(config.today, error=str(exc)),
                    503,
                )
                return

            action = next(
                (
                    item
                    for item in plan["actions"]
                    if item["invoice_id"] == form["invoice_id"]
                    and item["step"] == form["step"]
                ),
                None,
            )

            if action is None:
                self.send_error(
                    404,
                    "This reminder is no longer in today's plan",
                )
                return

            if not action["needs_approval"]:
                self.send_error(
                    400,
                    "This reminder does not require approval",
                )
                return

            key = (
                config.today,
                action["invoice_id"],
                action["step"],
            )
            with decision_lock:
                decisions[key] = form["decision"]

            # Refreshing the destination performs GET, not another POST.
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

    return ThreadingHTTPServer(("127.0.0.1", config.port), Handler)


def main():
    try:
        config = Config.from_env()
        server = create_server(config)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Serving on http://localhost:{config.port}/")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())