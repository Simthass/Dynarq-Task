"""Exercise the real CLI with isolated temporary files."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_plan import TODAY, invoice

PLAN_SCRIPT = Path(__file__).resolve().parents[1] / "plan.py"


class CliTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        self.root = Path(directory.name)
        self.invoices_path = self.root / "invoices.json"
        self.sent_path = self.root / "sent.json"
        self.output_path = self.root / "actions.json"

        self.write_json(self.invoices_path, [invoice()])
        self.write_json(self.sent_path, [])

    def write_json(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def run_cli(self, today=TODAY):
        return subprocess.run(
            [
                sys.executable,
                str(PLAN_SCRIPT),
                "--invoices",
                str(self.invoices_path),
                "--sent",
                str(self.sent_path),
                "--today",
                today,
                "--out",
                str(self.output_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def assert_failure(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_success_writes_expected_plan(self):
        result = self.run_cli()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

        output = self.output_path.read_text(encoding="utf-8")
        self.assertTrue(output.endswith("\n"))

        plan = json.loads(output)
        self.assertEqual(plan["today"], TODAY)
        self.assertEqual(plan["skipped"], [])
        self.assertEqual(len(plan["actions"]), 1)
        self.assertEqual(plan["actions"][0]["step"], "firm")

    def test_invalid_today_does_not_overwrite_output(self):
        self.output_path.write_text(
            "existing output", encoding="utf-8"
        )

        for today in (
            "2026-02-30",
            "2026-10-2",
            "20261012",
            "",
        ):
            with self.subTest(today=today):
                self.assert_failure(self.run_cli(today), "--today")
                self.assertEqual(
                    self.output_path.read_text(encoding="utf-8"),
                    "existing output",
                )

    def test_missing_input_files(self):
        for path in (self.invoices_path, self.sent_path):
            with self.subTest(path=path.name):
                original = path.read_text(encoding="utf-8")
                path.unlink()

                self.assert_failure(
                    self.run_cli(),
                    f"Cannot read '{path}'",
                )
                self.assertFalse(self.output_path.exists())

                path.write_text(original, encoding="utf-8")

    def test_malformed_json(self):
        for path in (self.invoices_path, self.sent_path):
            with self.subTest(path=path.name):
                original = path.read_text(encoding="utf-8")
                path.write_text("[broken", encoding="utf-8")

                self.assert_failure(
                    self.run_cli(),
                    f"Invalid JSON in '{path}'",
                )

                path.write_text(original, encoding="utf-8")

    def test_invalid_utf8(self):
        self.invoices_path.write_bytes(b"\xff\xfe")
        self.assert_failure(self.run_cli(), "Invalid JSON")

    def test_nonstandard_json_numbers(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                self.invoices_path.write_text(
                    '[{"amount": ' + value + '}]',
                    encoding="utf-8",
                )
                self.assert_failure(
                    self.run_cli(),
                    "Invalid JSON number",
                )

    def test_top_level_must_be_a_list(self):
        for path, name in (
            (self.invoices_path, "invoices"),
            (self.sent_path, "sent"),
        ):
            with self.subTest(name=name):
                original = path.read_text(encoding="utf-8")
                self.write_json(path, {})

                self.assert_failure(
                    self.run_cli(),
                    f"{name} must contain a JSON list",
                )

                path.write_text(original, encoding="utf-8")

    def test_records_must_be_objects(self):
        for path, name in (
            (self.invoices_path, "invoices"),
            (self.sent_path, "sent"),
        ):
            with self.subTest(name=name):
                original = path.read_text(encoding="utf-8")
                self.write_json(path, [None])

                self.assert_failure(
                    self.run_cli(),
                    f"{name}[0] must be a JSON object",
                )

                path.write_text(original, encoding="utf-8")

    def test_required_text_fields(self):
        for field in ("id", "customer", "currency"):
            with self.subTest(field=field):
                self.write_json(
                    self.invoices_path,
                    [invoice(**{field: None})],
                )

                self.assert_failure(
                    self.run_cli(),
                    f"invoices[0].{field} must be text",
                )

    def test_output_write_failure(self):
        # A directory cannot be opened as the output file.
        self.output_path = self.root
        self.assert_failure(self.run_cli(), "Cannot write")


if __name__ == "__main__":
    unittest.main()