# Payment Reminder Assistant

A local invoice-reminder planner and owner review page. Nothing is emailed.

## Requirements

Python 3.11 or newer. Standard library only; no installation, API key, or internet needed.

## Run

Run these commands from `python/`:

- Tests: `python -m unittest -v`
- Plan: `python plan.py --invoices ../data/invoices.json --sent ../data/sent.json --today 2026-10-12 --out ../actions.json`
- Page: `python app.py`, then open `http://localhost:8000/`.
  The page reads `PORT` (default `8000`), `DATA_DIR` (default `../data`), and `TODAY` (default the local date).
  For the sample date in PowerShell: `$env:TODAY = "2026-10-12"` before starting the page.

## Decisions

The CLI and page share one deterministic rules engine; reminder messages use offline templates.
Validation follows the specified precedence; duplicate IDs are excluded and reported once.
Only the highest eligible reminder is planned; a previously sent equal or higher step suppresses it.
Approvals and rejections remain in memory until restart and never update the input files.
The page supports keyboard controls, escaped invoice text, and a responsive mobile layout.
Research answers use only the supplied sources; no legal charges are added to messages.

## With more time

Add durable decision storage, broader browser accessibility checks, and authenticated access before hosting.
