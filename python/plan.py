"""Payment reminder rules engine and command-line interface."""

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import date

from messages import build_message

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


def validate_inputs(invoices, sent):
    """Reject structures outside the documented input contract."""
    for name, records in (("invoices", invoices), ("sent", sent)):
        if not isinstance(records, list):
            raise ValueError(f"{name} must contain a JSON list")

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(
                    f"{name}[{index}] must be a JSON object"
                )

            # These fields are guaranteed by the task specification.
            # Amount and dates remain invoice-level validation errors.
            if name == "invoices":
                for field in ("id", "customer", "currency"):
                    if not isinstance(record.get(field), str):
                        raise ValueError(
                            f"invoices[{index}].{field} must be text"
                        )


def build_plan(invoices, sent, today):
    """Return a deterministic plan without modifying inputs or sending messages."""
    today_date = parse_date(today)
    validate_inputs(invoices, sent)

    counts = Counter(invoice["id"] for invoice in invoices)
    duplicate_ids = {
        invoice_id
        for invoice_id, count in counts.items()
        if count > 1
    }

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

        if invoice.get("paid_date") is not None:
            continue

        days_overdue = (
            today_date - parse_date(invoice["due_date"])
        ).days

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


def reject_json_constant(value):
    """NaN and Infinity are Python extensions, not valid JSON numbers."""
    raise ValueError(f"Invalid JSON number: {value}")


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, parse_constant=reject_json_constant)
    except OSError as exc:
        raise ValueError(
            f"Cannot read '{path}': {exc.strerror or str(exc)}"
        ) from exc
    except (ValueError, UnicodeError) as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc


def main():
    parser = argparse.ArgumentParser(
        description="Plan today's payment reminders."
    )
    parser.add_argument("--invoices", required=True, help="path to invoices.json")
    parser.add_argument("--sent", required=True, help="path to sent.json")
    parser.add_argument("--today", required=True, help="date as YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="path to write the plan JSON")
    args = parser.parse_args()

    try:
        try:
            parse_date(args.today)
        except ValueError as exc:
            raise ValueError(
                "--today must be a real date in YYYY-MM-DD format"
            ) from exc

        invoices = read_json(args.invoices)
        sent = read_json(args.sent)
        plan = build_plan(invoices, sent, args.today)

        # Serialize before opening the destination.
        # Invalid input must not overwrite an existing output file.
        output = json.dumps(plan, indent=2, allow_nan=False) + "\n"

        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
        except OSError as exc:
            raise ValueError(
                f"Cannot write '{args.out}': {exc.strerror or str(exc)}"
            ) from exc

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())