"""Deterministic reminder messages that work without keys or internet access."""

REQUESTS = {
    "friendly": (
        "Just a friendly reminder to arrange payment when you have a moment. "
        "If you have a question about the invoice, please reply so we can help."
    ),
    "firm": (
        "Please arrange payment of the outstanding amount and reply with an "
        "update on its status. If there is an issue with the invoice, "
        "please let us know."
    ),
    "final": (
        "Please treat this outstanding payment as a priority. Arrange payment "
        "and reply to confirm its status, or let us know if there is an issue "
        "that needs to be resolved."
    ),
}


def build_message(invoice, step, days_overdue):
    """Render validated invoice facts with a fixed request for the selected step."""
    if step not in REQUESTS:
        raise ValueError(f"Unknown reminder step: {step}")

    amount = f"{invoice['currency']} {invoice['amount']:.2f}"

    return (
        f"Hello {invoice['customer']},\n\n"
        f"Invoice {invoice['id']} for {amount} was due on "
        f"{invoice['due_date']} and is {days_overdue} days overdue.\n\n"
        f"{REQUESTS[step]}\n\n"
        "Thank you."
    )