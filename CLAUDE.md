# CLAUDE.md — Optima Payment

Guidance for Claude Code when working in this app. This complements the bench-level
`/home/erpnext/fawaz/CLAUDE.md`; the rules there (especially **always ask which site**
before running `bench` commands) still apply.

## What this app is

An ERPNext v15 app for Saudi businesses that extends payments with: post-dated cheque
lifecycle management, company/petty-cash expenses, cheque printing, **Bank Guarantee-BG**,
and **Letter of Credit**. It adds custom fields/property setters to other apps' doctypes
(Payment Entry, Bank Account, Mode of Payment, …) via a setup framework — those cannot live
in this app's own DocType JSON.

## Layout

```
optima_payment/
  hooks.py                     # doc_events, fixtures, wiring
  install.py / migrate.py / uninstall.py   # setup lifecycle entry points
  setup/                       # feature framework: registry, runner, metadata, features/*
  optima_payment/doctype/      # this app's doctypes (bank_guarantee_bg, letter_of_credit, cheque_*)
  cheque/                      # cheque GL + payment entry override logic
  override/                    # Python class / whitelist overrides
  tests/utils.py               # SHARED test factories (import these, don't build docs inline)
docs/                          # developer + user documentation (start at docs/README.md)
```

## Accounting patterns (important)

Two doctypes book collateral through the ledger, but differently — don't conflate them:

- **Bank Guarantee-BG** writes **raw `GL Entry` rows** directly. Its tests assert GL rows.
- **Letter of Credit** posts via **system-generated Payment Entry (Internal Transfer)**
  documents, linked by the `letter_of_credit` field and tagged with `is_lc_*` flags. Its
  tests assert those Payment Entries. See `docs/letter-of-credit.md`.

For both, per-company accounts live on **Optima Payment Setting** and are validated as
mandatory before submit. Issue **commission is never reversed** on return/cancel.

## Tests

- `FrappeTestCase` (unittest), live-DB integration style, isolated by `frappe.db.rollback()`
  in `tearDown`. No mocking.
- Build fixtures with the factories in `optima_payment/tests/utils.py`
  (`make_optima_payment_setting`, `make_bank_guarantee_bg`, `make_letter_of_credit`). They
  are defensive and work around this bench's KSA/ZATCA mandatory-field customizations.
- Run: `bench --site <site> run-tests --module optima_payment.optima_payment.doctype.letter_of_credit.test_letter_of_credit`
- CI (`.github/workflows/ci.yml`, targets `version-15`) **auto-discovers every `test_*.py`**
  under the package via `rglob` — new test files need no registration. Some assertions skip
  on sites with extra customizations (e.g. the WTS cost-center rule); CI's `test_site` has
  none, so they run fully there. Details in `docs/testing.md`.

## Docs

`docs/` is the source of truth for how things work. When you change behavior, update the
matching doc. Index: `docs/README.md`.
