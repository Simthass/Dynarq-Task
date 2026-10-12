"""Accessible, responsive HTML rendering; business rules live in plan.py."""

from html import escape

REASONS = {
    "duplicate_id": (
        "This invoice ID appears more than once. "
        "Give each invoice a unique ID."
    ),
    "invalid_amount": (
        "The amount must be a number greater than zero."
    ),
    "missing_due_date": (
        "The due date is missing. Add it in YYYY-MM-DD format."
    ),
    "invalid_due_date": (
        "The due date must be a real date in YYYY-MM-DD format."
    ),
    "invalid_paid_date": (
        "The payment date must be a real date on or before today, "
        "or left unset if unpaid."
    ),
}

STYLES = """
:root {
  color-scheme: light;
  font-family: system-ui, sans-serif;
  color: #182230;
  background: #f7f8fa;
}
* { box-sizing: border-box; }
body { margin: 0; line-height: 1.6; }
a { color: #174fa3; }
:focus-visible {
  outline: 3px solid #174fa3;
  outline-offset: 4px;
}
.skip-link {
  position: absolute;
  left: 16px;
  top: -100px;
  padding: 12px 16px;
  background: white;
  z-index: 10;
}
.skip-link:focus { top: 16px; }
main {
  max-width: 1100px;
  margin: auto;
  padding: 48px 28px;
}
h1, h2, h3 {
  line-height: 1.25;
  letter-spacing: -0.025em;
}
h1 {
  font-size: clamp(1.9rem, 4vw, 2.7rem);
  margin: 8px 0 12px;
}
h2 { font-size: 1.35rem; margin: 0 0 8px; }
h3 {
  font-size: 1.15rem;
  margin: 12px 0 0;
  overflow-wrap: anywhere;
}
p { margin: 8px 0; }
.eyebrow {
  color: #49576a;
  font-size: .8rem;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
}
.page-header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 28px;
  border-bottom: 1px solid #d5dce5;
}
.intro { max-width: 610px; color: #49576a; }
.date {
  flex-shrink: 0;
  padding: 8px 12px;
  background: white;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  font-size: .9rem;
}
.notice {
  margin-top: 18px;
  color: #49576a;
  font-size: .9rem;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 28px;
}
.stat {
  border: 1px solid #d5dce5;
  border-radius: 12px;
  background: white;
  padding: 20px;
}
.stat p { margin: 0; font-weight: 650; }
section { margin-top: 36px; }
.section-note { color: #49576a; margin-bottom: 18px; }
.cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.card {
  min-width: 0;
  padding: 24px;
  border: 1px solid #d5dce5;
  border-radius: 14px;
  background: white;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.invoice-id {
  color: #49576a;
  font-size: .85rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}
.badge {
  padding: 3px 10px;
  border-radius: 6px;
  background: #edf3fc;
  color: #174fa3;
  font-size: .8rem;
  font-weight: 650;
}
dl {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 8px 16px;
  margin: 20px 0;
  font-size: .95rem;
}
dt { color: #49576a; }
dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 550;
}
.card[data-status="approved"] {
  border-left: 4px solid #23734a;
}
.card[data-status="rejected"] {
  border-left: 4px solid #8c3d32;
}
details {
  margin: 20px 0;
  border-top: 1px solid #e5e9ef;
  padding-top: 12px;
}
summary {
  cursor: pointer;
  min-height: 44px;
  padding: 8px 0;
  font-weight: 650;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  font-size: .93rem;
  line-height: 1.7;
  padding: 16px;
  background: #f7f8fa;
  border: 1px solid #e5e9ef;
  border-radius: 8px;
  margin: 8px 0 0;
}
form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
button {
  flex: 1;
  min-height: 44px;
  padding: 10px 16px;
  border: 1px solid #174fa3;
  border-radius: 8px;
  background: white;
  color: #174fa3;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}
button[value="approved"] {
  background: #174fa3;
  color: white;
}
button:hover { background: #edf3fc; }
button[value="approved"]:hover { background: #123e80; }
.skipped {
  list-style: none;
  padding: 0;
  margin: 18px 0 0;
}
.skipped li {
  padding: 18px 20px;
  border: 1px solid #d5dce5;
  border-radius: 10px;
  background: white;
  margin-bottom: 12px;
}
.skipped strong { overflow-wrap: anywhere; }
.skipped p { color: #49576a; margin-bottom: 0; }
.empty, .error-panel {
  padding: 24px;
  background: white;
  border: 1px solid #d5dce5;
  border-radius: 12px;
}
.error { overflow-wrap: anywhere; color: #8c3d32; }
.retry {
  display: inline-block;
  min-height: 44px;
  padding: 10px 0;
  font-weight: 650;
}
footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #d5dce5;
  color: #49576a;
  font-size: .9rem;
}
@media (max-width: 700px) {
  main { padding: 28px 16px; }
  .page-header { flex-direction: column; gap: 12px; }
  .stats { grid-template-columns: 1fr; gap: 10px; }
  .stat { padding: 14px 18px; }
  .cards { grid-template-columns: 1fr; }
  .card { padding: 20px; }
  dl {
    grid-template-columns: 100px minmax(0, 1fr);
    gap: 8px 12px;
  }
}
"""


def text(value):
    """Escape all data before inserting it into HTML."""
    return escape(str(value), quote=True)


def render_action(action, invoice, decision=None, csrf_token=""):
    status = (
        "Awaiting approval"
        if action["needs_approval"]
        else "No approval required"
    )
    if decision is not None:
        status = decision.capitalize()

    controls = ""
    if action["needs_approval"]:
        controls = f"""
        <form method="post" action="/decision">
          <input type="hidden" name="invoice_id"
            value="{text(action['invoice_id'])}">
          <input type="hidden" name="step"
            value="{text(action['step'])}">
          <input type="hidden" name="csrf_token" value="{text(csrf_token)}">
          <button type="submit" name="decision" value="approved"
            aria-label="Approve {text(action['step'])} reminder for {text(action['invoice_id'])}">
            Approve
          </button>
          <button type="submit" name="decision" value="rejected"
            aria-label="Reject {text(action['step'])} reminder for {text(action['invoice_id'])}">
            Reject
          </button>
        </form>"""

    amount = f"{invoice['currency']} {invoice['amount']:.2f}"

    return f"""
    <article class="card" data-status="{text(decision or 'pending')}">
      <div class="card-header">
        <span class="invoice-id">{text(action['invoice_id'])}</span>
        <span class="badge">{text(action['step'].capitalize())}</span>
      </div>
      <h3>{text(invoice['customer'])}</h3>
      <dl>
        <dt>Invoice</dt><dd>{text(action['invoice_id'])}</dd>
        <dt>Amount</dt><dd>{text(amount)}</dd>
        <dt>Days overdue</dt><dd>{text(action['days_overdue'])}</dd>
        <dt>Reminder</dt><dd>{text(action['step'].capitalize())}</dd>
        <dt>Status</dt><dd>{text(status)}</dd>
      </dl>
      <details open>
        <summary>Message preview</summary>
        <pre>{text(action['message'])}</pre>
      </details>
      {controls}
    </article>"""


def render_group(
    heading,
    heading_id,
    note,
    actions,
    by_id,
    today,
    decisions,
    csrf_token,
):
    cards = "".join(
        render_action(
            action,
            by_id[action["invoice_id"]],
            decisions.get(
                (today, action["invoice_id"], action["step"])
            ),
            csrf_token,
        )
        for action in actions
    )

    return f"""
    <section aria-labelledby="{heading_id}">
      <h2 id="{heading_id}">{heading}</h2>
      <p class="section-note">{note}</p>
      <div class="cards">{cards}</div>
    </section>"""


def render_page(
    today,
    invoices=None,
    plan=None,
    error=None,
    decisions=None,
    csrf_token="",
):
    decisions = {} if decisions is None else decisions

    if error is not None:
        content = f"""
        <section class="error-panel" aria-labelledby="error-heading">
          <h2 id="error-heading">We could not load today's plan</h2>
          <p>No reminders can be reviewed until the data is available.</p>
          <p class="error" role="alert">{text(error)}</p>
          <p>Check the invoice and reminder files, then reload this page.</p>
          <a class="retry" href="/">Try again</a>
        </section>"""
    else:
        by_id = {invoice["id"]: invoice for invoice in invoices}
        actions = plan["actions"]
        skipped = plan["skipped"]

        approval_count = sum(
            action["needs_approval"]
            and (today, action["invoice_id"], action["step"]) not in decisions
            for action in actions
        )

        content = f"""
        <div class="stats" aria-label="Plan summary">
          <div class="stat">
            <p>{len(actions)} reminders to review</p>
          </div>
          <div class="stat">
            <p>{approval_count} awaiting approval</p>
          </div>
          <div class="stat">
            <p>{len(skipped)} invoices need correction</p>
          </div>
        </div>"""

        if not actions:
            content += """
            <section class="empty" aria-labelledby="empty-heading">
              <h2 id="empty-heading">You're up to date</h2>
              <p>No reminders are due today for the invoices we could check.</p>
            </section>"""

        groups = (
            (
                True,
                "Approval decisions",
                "approval-heading",
                "Review each firm or final reminder. "
                "You can change a recorded decision.",
            ),
            (
                False,
                "No approval needed",
                "friendly-heading",
                "Friendly reminders are ready for your review.",
            ),
        )

        for needs_approval, heading, heading_id, note in groups:
            group = [
                action
                for action in actions
                if action["needs_approval"] == needs_approval
            ]
            if group:
                content += render_group(
                    heading,
                    heading_id,
                    note,
                    group,
                    by_id,
                    today,
                    decisions,
                    csrf_token,
                )

        content += """
        <section aria-labelledby="skipped-heading">
          <h2 id="skipped-heading">Invoices needing correction</h2>"""

        if skipped:
            content += """
            <p class="section-note">
              These invoices were excluded from the plan.
              Correct their data and reload the page.
            </p>
            <ul class="skipped">"""

            for item in skipped:
                content += (
                    f"<li><strong>{text(item['invoice_id'])}</strong>"
                    f"<p>{text(REASONS[item['reason']])}</p></li>"
                )

            content += "</ul>"
        else:
            content += (
                '<p class="section-note">'
                "No invoice data issues found.</p>"
            )

        content += "</section>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Payment reminders</title>
  <style>{STYLES}</style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to reminders</a>
  <main id="main-content" tabindex="-1">
    <header class="page-header">
      <div>
        <p class="eyebrow">Today's workspace</p>
        <h1>Payment reminders</h1>
        <p class="intro">
          A clear view of overdue invoices, reminder messages,
          and the decisions that need your attention.
        </p>
      </div>
      <p class="date">
        Plan for <time datetime="{text(today)}">{text(today)}</time>
      </p>
    </header>
    <p class="notice">
      Nothing is sent by this app.
      Approving or rejecting only records your decision.
    </p>
    {content}
    <footer>
      Decisions are kept until the app restarts.
      Invoice and sent-reminder files are unchanged.
    </footer>
  </main>
</body>
</html>"""