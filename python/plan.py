"""Payment reminder rules engine and command-line interface."""

import argparse
import json
import math
import re
from collections import Counter
from datetime import date

from messages import build_message

# Minimum overdue days, reminder step, approval requirement.
STEPS = (
    (3, "friendly", False),
    (10, "firm", True),
    (24, "final", True),
)
STEP_RANK = {
    step: rank
    for rank, (_, step, _) in enumerate(STEPS)
}


def parse_date(value):
    """Accept only real calendar dates written exactly as YYYY-MM-DD."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Expected a real date in YYYY-MM-DD format")
    return date.fromisoformat(value)


def validation_reason(invoice, today, duplicate_ids):
    """Return the first applicable skipped reason, or None."""
    if invoice["id"] in duplicate_ids:
        return "duplicate_id"

    amount = invoice.get("amount")

    # JSON booleans are not amounts, although bool subclasses int in Python.
    if type(amount) not in (int, float):
        return "invalid_amount"
    if isinstance(amount, float) and not math.isfinite(amount):
        return "invalid_amount"
    if amount <= 0:
        return "invalid_amount"

    due_date = invoice.get("due_date")
    if due_date is None or due_date == "":
        return "missing_due_date"

    try:
        parse_date(due_date)
    except ValueError:
        return "invalid_due_date"

    paid_date = invoice.get("paid_date")
    if paid_date is not None:
        try:
            if parse_date(paid_date) > today:
                return "invalid_paid_date"
        except ValueError:
            return "invalid_paid_date"

    return None


def build_plan(invoices, sent, today):
    """Return a deterministic plan without modifying inputs or sending messages."""
    today_date = parse_date(today)

    # Count first so every occurrence of a duplicate ID is excluded.
    counts = Counter(invoice["id"] for invoice in invoices)
    duplicate_ids = {
        invoice_id
        for invoice_id, count in counts.items()
        if count > 1
    }

    # Retain the highest known reminder step for each invoice.
    highest_sent = {}
    for reminder in sent:
        invoice_id = reminder.get("invoice_id")
        step = reminder.get("step")

        if not isinstance(invoice_id, str) or invoice_id not in counts:
            continue
        if not isinstance(step, str) or step not in STEP_RANK:
            continue

        highest_sent[invoice_id] = max(
            highest_sent.get(invoice_id, -1),
            STEP_RANK[step],
        )

    skipped = {}
    actions = []

    for invoice in invoices:
        invoice_id = invoice["id"]
        reason = validation_reason(invoice, today_date, duplicate_ids)

        if reason is not None:
            skipped[invoice_id] = reason
            continue

        # Validation has already rejected invalid or future payment dates.
        if invoice.get("paid_date") is not None:
            continue

        days_overdue = (
            today_date - parse_date(invoice["due_date"])
        ).days

        # Search highest threshold first; generate at most one action.
        selected = next(
            (
                rule
                for rule in reversed(STEPS)
                if days_overdue >= rule[0]
            ),
            None,
        )
        if selected is None:
            continue

        _, step, needs_approval = selected

        if highest_sent.get(invoice_id, -1) >= STEP_RANK[step]:
            continue

        actions.append({
            "invoice_id": invoice_id,
            "step": step,
            "needs_approval": needs_approval,
            "days_overdue": days_overdue,
            "message": build_message(invoice, step, days_overdue),
        })

    return {
        "today": today,
        "actions": sorted(
            actions,
            key=lambda action: action["invoice_id"],
        ),
        "skipped": [
            {"invoice_id": invoice_id, "reason": skipped[invoice_id]}
            for invoice_id in sorted(skipped)
        ],
    }


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Plan today's payment reminders."
    )
    parser.add_argument("--invoices", required=True, help="path to invoices.json")
    parser.add_argument("--sent", required=True, help="path to sent.json")
    parser.add_argument("--today", required=True, help="date as YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="path to write the plan JSON")
    args = parser.parse_args()

    invoices = read_json(args.invoices)
    sent = read_json(args.sent)
    plan = build_plan(invoices, sent, args.today)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()