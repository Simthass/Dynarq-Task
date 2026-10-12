"""Configuration and HTTP tests for the owner's page."""

import json
import tempfile
import threading
import unittest
from datetime import date
from http.client import HTTPConnection
from pathlib import Path

from app import Config, create_server
from tests.test_plan import TODAY, invoice


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = Config.from_env({})

        self.assertEqual(config.port, 8000)
        self.assertEqual(config.data_dir, Path("../data"))
        self.assertEqual(config.today, date.today().isoformat())

    def test_environment_overrides(self):
        config = Config.from_env({
            "PORT": "9001",
            "DATA_DIR": "custom-data",
            "TODAY": TODAY,
        })

        self.assertEqual(
            config,
            Config(9001, Path("custom-data"), TODAY),
        )

    def test_invalid_configuration(self):
        cases = (
            {"PORT": "abc"},
            {"PORT": "0"},
            {"PORT": "65536"},
            {"TODAY": "2026-02-30"},
            {"TODAY": ""},
        )

        for environment in cases:
            with self.subTest(environment=environment):
                with self.assertRaises(ValueError):
                    Config.from_env(environment)


class PageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        self.root = Path(directory.name)
        self.write_data([invoice()], [])

        # Port 0 lets the operating system choose an available test port.
        self.server = create_server(Config(0, self.root, TODAY))
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(
                poll_interval=0.05
            ),
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def write_data(self, invoices, sent):
        (self.root / "invoices.json").write_text(
            json.dumps(invoices),
            encoding="utf-8",
        )
        (self.root / "sent.json").write_text(
            json.dumps(sent),
            encoding="utf-8",
        )

    def get(self, path="/"):
        connection = HTTPConnection(
            "127.0.0.1",
            self.server.server_port,
            timeout=5,
        )
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return (
                response.status,
                dict(response.getheaders()),
                response.read().decode("utf-8"),
            )
        finally:
            connection.close()

    def test_plan_details_and_message(self):
        status, headers, body = self.get()

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertEqual(headers["Cache-Control"], "no-store")

        for expected in (
            TODAY,
            "Example Ltd",
            "INV-1",
            "EUR 1250.00",
            "Firm",
            "Awaiting approval",
            "12 days overdue",
            "Nothing is sent",
        ):
            self.assertIn(expected, body)

    def test_page_uses_sent_history(self):
        self.write_data(
            [invoice()],
            [{"invoice_id": "INV-1", "step": "firm"}],
        )
        _, _, body = self.get()

        self.assertIn("No reminders are due today", body)
        self.assertNotIn("Message preview", body)

    def test_empty_plan(self):
        self.write_data([], [])
        status, _, body = self.get()

        self.assertEqual(status, 200)
        self.assertIn("No reminders are due today", body)
        self.assertIn("No invoice data issues found", body)

    def test_skipped_reason_is_plain_language(self):
        self.write_data(
            [invoice(due_date="2026-02-30")],
            [],
        )
        status, _, body = self.get()

        self.assertEqual(status, 200)
        self.assertIn("INV-1", body)
        self.assertIn("The due date must be a real date", body)
        self.assertNotIn("invalid_due_date", body)

    def test_unreadable_data_has_error_page(self):
        (self.root / "invoices.json").unlink()
        status, _, body = self.get()

        self.assertEqual(status, 503)
        self.assertIn("We could not load today's plan", body)
        self.assertIn("Try again", body)
        self.assertNotIn("Message preview", body)

    def test_html_is_escaped(self):
        self.write_data(
            [invoice(customer='<script>alert("x")</script>')],
            [],
        )
        status, _, body = self.get()

        self.assertEqual(status, 200)
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)

    def test_unknown_route(self):
        status, _, _ = self.get("/unknown")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()