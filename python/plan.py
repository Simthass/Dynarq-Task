"""Payment reminder planner.

Run from inside python/:
    python plan.py --invoices ../data/invoices.json \
        --sent ../data/sent.json --today 2026-10-12 \
        --out ../actions.json
"""

import argparse
import json
import math
import re
from collections import Counter
from datetime import date


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
    """Validate invoices; reminder selection is the next implementation step."""
    today_date = parse_date(today)

    # Count first so every occurrence of a duplicate ID is excluded.
    counts = Counter(invoice["id"] for invoice in invoices)
    duplicate_ids = {
        invoice_id
        for invoice_id, count in counts.items()
        if count > 1
    }

    # Keying by ID reports a duplicate only once.
    skipped = {}
    for invoice in invoices:
        reason = validation_reason(invoice, today_date, duplicate_ids)
        if reason is not None:
            skipped[invoice["id"]] = reason

    return {
        "today": today,
        "actions": [],
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