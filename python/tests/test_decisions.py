"""HTTP tests for in-memory approval decisions."""

import json
import re
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode

from app import Config, create_server
from tests.test_plan import TODAY, invoice


class DecisionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

        (self.root / "invoices.json").write_text(
            json.dumps([
                invoice(),
                invoice(id="INV-2", due_date="2026-09-01"),
                invoice(id="INV-3", due_date="2026-10-09"),
            ]),
            encoding="utf-8",
        )
        (self.root / "sent.json").write_text("[]", encoding="utf-8")

        self.server = create_server(Config(0, self.root, TODAY))
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(
                poll_interval=0.05
            ),
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

        _, _, page = self.request("GET", "/")
        self.token = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            page,
        ).group(1)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection(
            "127.0.0.1",
            self.server.server_port,
            timeout=5,
        )
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return (
                response.status,
                dict(response.getheaders()),
                response.read().decode("utf-8"),
            )
        finally:
            connection.close()

    def decide(self, **changes):
        form = {
            "invoice_id": "INV-1",
            "step": "firm",
            "decision": "approved",
            "csrf_token": self.token,
        }
        form.update(changes)

        return self.request(
            "POST",
            "/decision",
            urlencode(form),
            {"Content-Type": "application/x-www-form-urlencoded"},
        )

    def test_approve_and_reject_persist_after_refresh(self):
        for decision, label in (
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ):
            with self.subTest(decision=decision):
                status, headers, _ = self.decide(decision=decision)

                self.assertEqual(status, 303)
                self.assertEqual(headers["Location"], "/")

                for _ in range(2):
                    _, _, page = self.request("GET", "/")
                    self.assertIn(f"<dd>{label}</dd>", page)
                    self.assertIn("1 awaiting approval", page)

    def test_final_reminder_can_be_approved(self):
        self.assertEqual(
            self.decide(invoice_id="INV-2", step="final")[0],
            303,
        )

    def test_friendly_reminder_cannot_be_approved(self):
        self.assertEqual(
            self.decide(invoice_id="INV-3", step="friendly")[0],
            400,
        )

    def test_invalid_decision(self):
        self.assertEqual(self.decide(decision="send")[0], 400)

    def test_unknown_or_mismatched_action(self):
        self.assertEqual(self.decide(invoice_id="UNKNOWN")[0], 404)
        self.assertEqual(self.decide(step="final")[0], 404)

    def test_invalid_token(self):
        for token in ("wrong", "é"):
            with self.subTest(token=token):
                self.assertEqual(
                    self.decide(csrf_token=token)[0],
                    403,
                )

    def test_missing_fields(self):
        status, _, _ = self.request(
            "POST",
            "/decision",
            "decision=approved",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 400)

    def test_stale_action_is_rechecked(self):
        (self.root / "sent.json").write_text(
            json.dumps([
                {"invoice_id": "INV-1", "step": "firm"},
            ]),
            encoding="utf-8",
        )

        self.assertEqual(self.decide()[0], 404)

    def test_data_failure_does_not_record_decision(self):
        (self.root / "sent.json").unlink()
        self.assertEqual(self.decide()[0], 503)

        (self.root / "sent.json").write_text("[]", encoding="utf-8")
        _, _, page = self.request("GET", "/")

        self.assertNotIn("<dd>Approved</dd>", page)

    def test_decisions_do_not_modify_input_files(self):
        paths = [
            self.root / "invoices.json",
            self.root / "sent.json",
        ]
        original = [path.read_bytes() for path in paths]

        self.assertEqual(self.decide()[0], 303)
        self.assertEqual(
            [path.read_bytes() for path in paths],
            original,
        )


if __name__ == "__main__":
    unittest.main()