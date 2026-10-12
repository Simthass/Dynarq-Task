"""Message contracts: invoice facts, formatting, tone, and no invented figures."""

import re
import unittest
from unittest.mock import patch

from messages import build_message


def sample_invoice(**changes):
    record = {
        "id": "INV-1001",
        "customer": "Example Ltd",
        "currency": "EUR",
        "amount": 1250.0,
        "due_date": "2026-09-30",
    }
    record.update(changes)
    return record


class MessageTests(unittest.TestCase):
    def test_required_facts_for_every_step(self):
        record = sample_invoice()

        for step in ("friendly", "firm", "final"):
            with self.subTest(step=step):
                message = build_message(record, step, 12)

                for fact in (
                    record["customer"],
                    record["id"],
                    record["due_date"],
                    "EUR 1250.00",
                    "12 days overdue",
                ):
                    self.assertIn(fact, message)

    def test_amount_always_has_two_decimals(self):
        cases = (
            (1, "EUR 1.00"),
            (0.5, "EUR 0.50"),
            (845.25, "EUR 845.25"),
        )

        for amount, expected in cases:
            with self.subTest(amount=amount):
                message = build_message(
                    sample_invoice(amount=amount),
                    "friendly",
                    3,
                )
                self.assertIn(expected, message)

    def test_currency_is_taken_from_invoice(self):
        message = build_message(
            sample_invoice(currency="USD"),
            "firm",
            10,
        )

        self.assertIn("USD 1250.00", message)
        self.assertNotIn("EUR", message)

    def test_no_figures_beyond_required_invoice_facts(self):
        # Customer names and invoice IDs may legitimately contain digits.
        record = sample_invoice(
            customer="Studio 54",
            id="INV-2026-42",
            amount=845.25,
            currency="USD",
        )

        for step in ("friendly", "firm", "final"):
            with self.subTest(step=step):
                message = build_message(record, step, 24)
                allowed_facts = (
                    record["customer"],
                    record["id"],
                    record["due_date"],
                    "USD 845.25",
                    "24 days overdue",
                )

                # Remove each permitted fact once, then check for extra figures.
                remainder = message
                for fact in sorted(
                    allowed_facts,
                    key=len,
                    reverse=True,
                ):
                    self.assertIn(fact, remainder)
                    remainder = remainder.replace(fact, "", 1)

                self.assertIsNone(re.search(r"\d", remainder))

    def test_no_unsupported_financial_or_legal_claims(self):
        prohibited = (
            "fee",
            "interest",
            "penalty",
            "legal action",
            "debt collection",
            "ECB",
            "previous reminder",
            "earlier reminder",
            "already reminded",
            "within",
            "deadline",
            "tomorrow",
        )

        for step in ("friendly", "firm", "final"):
            with self.subTest(step=step):
                message = build_message(
                    sample_invoice(),
                    step,
                    24,
                ).lower()

                for phrase in prohibited:
                    self.assertNotIn(phrase.lower(), message)

    def test_tones_are_distinct(self):
        record = sample_invoice()

        friendly = build_message(record, "friendly", 24)
        firm = build_message(record, "firm", 24)
        final = build_message(record, "final", 24)

        self.assertIn("friendly reminder", friendly)
        self.assertIn("outstanding amount", firm)
        self.assertIn("as a priority", final)
        self.assertEqual(len({friendly, firm, final}), 3)

    def test_unknown_step_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unknown reminder step",
        ):
            build_message(sample_invoice(), "urgent", 24)

    def test_deterministic_without_environment_keys(self):
        record = sample_invoice()

        with patch.dict("os.environ", {}, clear=True):
            first = build_message(record, "firm", 10)
            second = build_message(record, "firm", 10)

        self.assertEqual(first, second)

    def test_unicode_names_are_preserved(self):
        customer = "Café Müller & Sons"

        self.assertIn(
            customer,
            build_message(
                sample_invoice(customer=customer),
                "friendly",
                3,
            ),
        )

    def test_invoice_is_not_modified(self):
        record = sample_invoice()
        original = record.copy()

        build_message(record, "final", 24)

        self.assertEqual(record, original)


if __name__ == "__main__":
    unittest.main()