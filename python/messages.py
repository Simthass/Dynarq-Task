"""Offline reminder templates containing only invoice facts."""

REQUESTS = {
    "friendly": (
        "When you have a moment, please arrange payment. "
        "If you have a question about the invoice, please reply."
    ),
    "firm": (
        "Please arrange payment and reply with an update on its status."
    ),
    "final": (
        "This payment requires your attention. "
        "Please arrange payment and reply to confirm its status."
    ),
}


def build_message(invoice, step, days_overdue):
    amount = f"{invoice['currency']} {invoice['amount']:.2f}"

    return (
        f"Hello {invoice['customer']},\n\n"
        f"Invoice {invoice['id']} for {amount} was due on "
        f"{invoice['due_date']} and is {days_overdue} days overdue.\n\n"
        f"{REQUESTS[step]}\n\n"
        "Thank you."
    )