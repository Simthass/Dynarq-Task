"""Tests for reminder selection, history suppression, and output contracts."""

import unittest
from datetime import date, timedelta

from plan import build_plan
from tests.test_plan import TODAY, invoice


def overdue_invoice(days, **changes):
    due_date = (
        date.fromisoformat(TODAY) - timedelta(days=days)
    ).isoformat()
    return invoice(due_date=due_date, **changes)


class ReminderRuleTests(unittest.TestCase):
    def test_threshold_boundaries(self):
        cases = (
            (-1, None),
            (0, None),
            (2, None),
            (3, "friendly"),
            (9, "friendly"),
            (10, "firm"),
            (23, "firm"),
            (24, "final"),
            (100, "final"),
        )

        for days, expected in cases:
            with self.subTest(days=days):
                actions = build_plan(
                    [overdue_invoice(days)], [], TODAY
                )["actions"]

                if expected is None:
                    self.assertEqual(actions, [])
                else:
                    self.assertEqual(len(actions), 1)
                    self.assertEqual(actions[0]["step"], expected)
                    self.assertEqual(actions[0]["days_overdue"], days)
                    self.assertEqual(
                        actions[0]["needs_approval"],
                        expected != "friendly",
                    )

    def test_selects_only_highest_step_without_history(self):
        actions = build_plan(
            [overdue_invoice(12)], [], TODAY
        )["actions"]

        self.assertEqual(
            [action["step"] for action in actions],
            ["firm"],
        )

    def test_all_sent_step_combinations(self):
        steps = ("friendly", "firm", "final")

        for days, selected in (
            (3, "friendly"),
            (10, "firm"),
            (24, "final"),
        ):
            for sent_step in steps:
                with self.subTest(
                    selected=selected,
                    sent_step=sent_step,
                ):
                    sent = [{
                        "invoice_id": "INV-1",
                        "step": sent_step,
                    }]
                    actions = build_plan(
                        [overdue_invoice(days)], sent, TODAY
                    )["actions"]

                    already_reached = (
                        steps.index(sent_step) >= steps.index(selected)
                    )
                    expected = [] if already_reached else [selected]

                    self.assertEqual(
                        [action["step"] for action in actions],
                        expected,
                    )

    def test_highest_history_step_wins_regardless_of_order(self):
        sent = [
            {"invoice_id": "INV-1", "step": step}
            for step in ("final", "friendly", "firm", "friendly")
        ]

        self.assertEqual(
            build_plan([overdue_invoice(30)], sent, TODAY)["actions"],
            [],
        )
        self.assertEqual(
            build_plan(
                [overdue_invoice(30)],
                list(reversed(sent)),
                TODAY,
            )["actions"],
            [],
        )

    def test_unknown_history_entries_are_ignored(self):
        sent = [
            {"invoice_id": "UNKNOWN", "step": "final"},
            {"invoice_id": "INV-1", "step": "unknown"},
        ]
        actions = build_plan(
            [overdue_invoice(12)], sent, TODAY
        )["actions"]

        self.assertEqual(
            [action["step"] for action in actions],
            ["firm"],
        )

    def test_sent_on_is_not_used(self):
        for value in ("2099-01-01", "not-a-date", None):
            with self.subTest(sent_on=value):
                sent = [{
                    "invoice_id": "INV-1",
                    "step": "firm",
                    "sent_on": value,
                }]

                self.assertEqual(
                    build_plan(
                        [overdue_invoice(12)], sent, TODAY
                    )["actions"],
                    [],
                )

    def test_paid_invoices_have_no_actions(self):
        for paid_date in ("2026-10-05", TODAY):
            with self.subTest(paid_date=paid_date):
                sent = [{
                    "invoice_id": "INV-1",
                    "step": "friendly",
                }]

                self.assertEqual(
                    build_plan(
                        [overdue_invoice(30, paid_date=paid_date)],
                        sent,
                        TODAY,
                    )["actions"],
                    [],
                )

    def test_missing_paid_date_is_unpaid(self):
        record = overdue_invoice(3)
        del record["paid_date"]

        self.assertEqual(
            len(build_plan([record], [], TODAY)["actions"]),
            1,
        )

    def test_invalid_invoices_never_generate_actions(self):
        records = [
            overdue_invoice(30, amount=0),
            overdue_invoice(
                30,
                id="INV-2",
                paid_date="2026-10-13",
            ),
        ]
        plan = build_plan(records, [], TODAY)

        self.assertEqual(plan["actions"], [])
        self.assertEqual(len(plan["skipped"]), 2)

    def test_duplicates_never_generate_actions(self):
        plan = build_plan(
            [overdue_invoice(30), overdue_invoice(12)],
            [],
            TODAY,
        )

        self.assertEqual(plan["actions"], [])
        self.assertEqual(
            plan["skipped"],
            [{"invoice_id": "INV-1", "reason": "duplicate_id"}],
        )

    def test_actions_use_plain_text_sorting(self):
        records = [
            overdue_invoice(3, id=value)
            for value in ("INV-99", "INV-100", "INV-2")
        ]
        actions = build_plan(records, [], TODAY)["actions"]

        self.assertEqual(
            [action["invoice_id"] for action in actions],
            ["INV-100", "INV-2", "INV-99"],
        )

    def test_exact_output_keys_and_required_message_facts(self):
        record = overdue_invoice(
            10,
            amount=845.25,
            currency="USD",
        )
        plan = build_plan([record], [], TODAY)

        self.assertEqual(
            set(plan),
            {"today", "actions", "skipped"},
        )

        action = plan["actions"][0]
        self.assertEqual(
            set(action),
            {
                "invoice_id",
                "step",
                "needs_approval",
                "days_overdue",
                "message",
            },
        )

        for fact in (
            record["customer"],
            record["id"],
            record["due_date"],
            "USD 845.25",
            "10 days overdue",
        ):
            self.assertIn(fact, action["message"])


if __name__ == "__main__":
    unittest.main()