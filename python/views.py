"""HTML rendering for the owner's page; business rules live in plan.py."""

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


def text(value):
    """Escape all data before inserting it into HTML."""
    return escape(str(value), quote=True)


def render_action(action, invoice):
    approval = (
        "Awaiting approval"
        if action["needs_approval"]
        else "No approval required"
    )
    amount = f"{invoice['currency']} {invoice['amount']:.2f}"

    return f"""
    <article class="card">
      <h3>{text(invoice['customer'])}</h3>
      <dl>
        <dt>Invoice</dt><dd>{text(action['invoice_id'])}</dd>
        <dt>Amount</dt><dd>{text(amount)}</dd>
        <dt>Days overdue</dt><dd>{text(action['days_overdue'])}</dd>
        <dt>Reminder</dt><dd>{text(action['step'].capitalize())}</dd>
        <dt>Status</dt><dd>{text(approval)}</dd>
      </dl>
      <h4>Message preview</h4>
      <pre>{text(action['message'])}</pre>
    </article>"""


def render_page(today, invoices=None, plan=None, error=None):
    if error is not None:
        content = f"""
        <section aria-labelledby="error-heading">
          <h2 id="error-heading">We could not load today's plan</h2>
          <p>No reminders can be reviewed until the data is available.</p>
          <p class="error" role="alert">{text(error)}</p>
          <p>Check the invoice and reminder files, then reload this page.</p>
          <a href="/">Try again</a>
        </section>"""
    else:
        by_id = {invoice["id"]: invoice for invoice in invoices}
        actions = plan["actions"]
        skipped = plan["skipped"]
        approval_count = sum(
            action["needs_approval"] for action in actions
        )

        content = f"""
        <p class="summary">
          {len(actions)} reminders to review ·
          {approval_count} need approval ·
          {len(skipped)} invoices need correction
        </p>
        <section aria-labelledby="reminders-heading">
          <h2 id="reminders-heading">Today's reminders</h2>"""

        if actions:
            content += "".join(
                render_action(action, by_id[action["invoice_id"]])
                for action in actions
            )
        else:
            content += (
                "<p>No reminders are due today "
                "for the invoices we could check.</p>"
            )

        content += """
        </section>
        <section aria-labelledby="skipped-heading">
          <h2 id="skipped-heading">Invoices needing correction</h2>"""

        if skipped:
            content += '<ul class="skipped">'

            for item in skipped:
                reason = REASONS[item["reason"]]
                content += (
                    f"<li><strong>{text(item['invoice_id'])}</strong>"
                    f"<p>{text(reason)}</p></li>"
                )

            content += "</ul>"
        else:
            content += "<p>No invoice data issues found.</p>"

        content += "</section>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Payment reminders</title>
  <style>
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #182230;
      font-family: system-ui, sans-serif;
      line-height: 1.6;
    }}
    main {{
      max-width: 920px;
      margin: auto;
      padding: 32px 20px;
    }}
    h1, h2, h3, h4 {{
      line-height: 1.3;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    section {{
      margin-top: 32px;
    }}
    .card, .skipped li {{
      padding: 20px;
      margin-bottom: 16px;
      border: 1px solid #d5dce5;
      border-radius: 12px;
      background: white;
    }}
    .card h3 {{
      margin-top: 0;
    }}
    dl {{
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      gap: 8px 16px;
    }}
    dt {{
      color: #49576a;
    }}
    dd {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font: inherit;
      padding: 16px;
      background: #f6f7f9;
      border-radius: 8px;
    }}
    .skipped {{
      list-style: none;
      padding: 0;
    }}
    .skipped p {{
      margin-bottom: 0;
    }}
    .error, h3, strong {{
      overflow-wrap: anywhere;
    }}
    a {{
      color: #174fa3;
    }}
    a:focus-visible {{
      outline: 3px solid #174fa3;
      outline-offset: 4px;
    }}
    @media (max-width: 480px) {{
      main {{
        padding: 24px 16px;
      }}
      .card {{
        padding: 16px;
      }}
      dl {{
        grid-template-columns: 100px minmax(0, 1fr);
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Payment reminders</h1>
      <p>Plan for <time datetime="{text(today)}">{text(today)}</time></p>
      <p>Review reminder messages here. Nothing is sent by this app.</p>
    </header>
    {content}
  </main>
</body>
</html>"""