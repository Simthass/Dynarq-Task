"""Owner's page. Run from python/: python app.py."""

import os
import sys
from dataclasses import dataclass
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

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
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path != "/":
                self.send_error(404)
                return

            try:
                invoices, plan = load_plan(config)
                body = render_page(config.today, invoices, plan)
                status = 200
            except ValueError as exc:
                body = render_page(config.today, error=str(exc))
                status = 503

            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

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