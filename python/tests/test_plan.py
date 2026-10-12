"""Run from inside python/: python -m unittest -v."""

import unittest

from plan import build_plan

TODAY = "2026-10-12"


def invoice(**changes):
    record = {
        "id": "INV-1",
        "customer": "Example Ltd",
        "currency": "EUR",
        "amount": 1250.0,
        "due_date": "2026-09-30",
        "paid_date": None,
    }
    record.update(changes)
    return record


class ValidationTests(unittest.TestCase):
    def assert_reason(self, record, reason):
        self.assertEqual(
            build_plan([record], [], TODAY)["skipped"],
            [{"invoice_id": record["id"], "reason": reason}],
        )

    def test_empty_input(self):
        self.assertEqual(
            build_plan([], [], TODAY),
            {"today": TODAY, "actions": [], "skipped": []},
        )

    def test_valid_invoices_are_not_skipped(self):
        for amount in (1, 0.01, 1250.0):
            with self.subTest(amount=amount):
                self.assertEqual(
                    build_plan([invoice(amount=amount)], [], TODAY)["skipped"],
                    [],
                )

    def test_invalid_amounts(self):
        invalid_amounts = (
            None,
            "1250",
            True,
            False,
            0,
            -1,
            [],
            {},
            float("nan"),
            float("inf"),
            -float("inf"),
        )
        for amount in invalid_amounts:
            with self.subTest(amount=amount):
                self.assert_reason(invoice(amount=amount), "invalid_amount")

        record = invoice()
        del record["amount"]
        self.assert_reason(record, "invalid_amount")

    def test_missing_due_dates(self):
        for value in (None, ""):
            with self.subTest(value=value):
                self.assert_reason(
                    invoice(due_date=value), "missing_due_date"
                )

        record = invoice()
        del record["due_date"]
        self.assert_reason(record, "missing_due_date")

    def test_invalid_due_dates(self):
        invalid_dates = (
            "2026-02-30",
            "2026-02-29",
            "30/09/2026",
            "2026-9-30",
            "20260930",
            "2026-09-30T00:00:00",
            " 2026-09-30",
            123,
            True,
            [],
            {},
        )
        for value in invalid_dates:
            with self.subTest(value=value):
                self.assert_reason(
                    invoice(due_date=value), "invalid_due_date"
                )

    def test_real_leap_day(self):
        self.assertEqual(
            build_plan(
                [invoice(due_date="2024-02-29")], [], TODAY
            )["skipped"],
            [],
        )

    def test_invalid_paid_dates(self):
        invalid_dates = (
            "",
            "2026-10-13",
            "2026-02-30",
            "2026-10-5",
            "20261005",
            "05/10/2026",
            123,
            False,
            [],
            {},
        )
        for value in invalid_dates:
            with self.subTest(value=value):
                self.assert_reason(
                    invoice(paid_date=value), "invalid_paid_date"
                )

    def test_valid_paid_dates_and_unpaid_values(self):
        for value in (None, "2026-10-05", TODAY):
            with self.subTest(value=value):
                self.assertEqual(
                    build_plan(
                        [invoice(paid_date=value)], [], TODAY
                    )["skipped"],
                    [],
                )

        record = invoice()
        del record["paid_date"]
        self.assertEqual(build_plan([record], [], TODAY)["skipped"], [])

    def test_duplicate_id_reported_once_and_before_other_errors(self):
        records = [
            invoice(amount=0),
            invoice(due_date=None),
            invoice(paid_date=""),
        ]
        self.assertEqual(
            build_plan(records, [], TODAY)["skipped"],
            [{"invoice_id": "INV-1", "reason": "duplicate_id"}],
        )

    def test_validation_precedence(self):
        self.assert_reason(
            invoice(amount=0, due_date=None, paid_date=""),
            "invalid_amount",
        )
        self.assert_reason(
            invoice(due_date=None, paid_date=""),
            "missing_due_date",
        )
        self.assert_reason(
            invoice(due_date="bad", paid_date=""),
            "invalid_due_date",
        )

    def test_bad_data_is_checked_even_when_paid(self):
        self.assert_reason(
            invoice(amount=0, paid_date=TODAY),
            "invalid_amount",
        )

    def test_skipped_ids_use_plain_text_sorting(self):
        records = [
            invoice(id=value, amount=0)
            for value in ("INV-99", "INV-100", "INV-2")
        ]
        self.assertEqual(
            [
                item["invoice_id"]
                for item in build_plan(records, [], TODAY)["skipped"]
            ],
            ["INV-100", "INV-2", "INV-99"],
        )

    def test_invalid_today(self):
        for value in ("2026-02-30", "2026-10-2", "20261012", "", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build_plan([], [], value)

    def test_inputs_are_not_modified(self):
        record = invoice(amount=0)
        original = record.copy()
        sent = [{"invoice_id": "INV-1", "step": "friendly"}]
        original_sent = [entry.copy() for entry in sent]

        build_plan([record], sent, TODAY)

        self.assertEqual(record, original)
        self.assertEqual(sent, original_sent)


if __name__ == "__main__":
    unittest.main()