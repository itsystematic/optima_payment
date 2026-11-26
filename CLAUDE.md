# CLAUDE.md — Optima Payment

Guidance for Claude Code when working in this app. This complements the bench-level
`/home/erpnext/fawaz/CLAUDE.md`; the rules there (especially **always ask which site**
before running `bench` commands) still apply.

## What this app is

An ERPNext app for Saudi businesses that extends payments with: post-dated cheque
lifecycle management, company/petty-cash expenses, cheque printing, **Bank Guarantee-BG**,
and **Letter of Credit**. It adds custom fields/property setters to other apps' doctypes
(Payment Entry, Bank Account, Mode of Payment, …) via a setup framework — those cannot live
in this app's own DocType JSON.

## Branches

`develop` (the default branch) and `version-16` target Frappe/ERPNext 16, and `version-15`
targets 15. Work lands on `develop`, `version-16` moves only by release merges from it, and
`version-15` gets PRs labelled `backport version-15`. Branch new work from `develop`, never
from a release branch. `CONTRIBUTING.md` has the full branch, backport and release rules.

## Layout

```
optima_payment/
  hooks.py                     # doc_events, fixtures, wiring
  install.py / migrate.py / uninstall.py   # setup lifecycle entry points
  setup/                       # customization framework: features/*, sync/, registry, permissions
  optima_payment/doctype/      # this app's doctypes (bank_guarantee_bg, letter_of_credit, cheque_*)
  cheque/                      # cheque GL + payment entry override logic
  purchases_bulk/              # Purchases Bulk Tool: pure decisions + voucher create/rollback (vouchers.py), form door (api.py)
  overdue_limit/               # Time Based Overdue Limit: pure decisions + queries + check (limit.py), hooked from doc_events/
  override/                    # Python class / whitelist overrides
  tests/utils.py               # SHARED test factories (import these, don't build docs inline)
docs/                          # developer + user documentation (start at docs/README.md)
```

## Customizations (important)

Client sites customize these same forms in Customize Form, and the app must never overwrite that.
Frappe's `is_system_generated` flag decides ownership: **1 = the app's row, 0 = the site's**.

- Declare fields and property setters in `setup/features/*`; `setup/sync/` applies them. It creates
  what is missing, updates only rows still at flag 1, and leaves every flag-0 row alone.
- **Never write `field_order`** outside `apply_starting_field_orders()` (install, only when the site
  has none) — it holds the client's whole layout. Never delete property setters by doctype +
  property alone; that matches the client's rows too.
- **Never change a fieldtype in place**: new fieldname + data patch + removal.
- Nothing re-applies the declarations on migrate. Every change ships as **one patch whose body calls
  `sync()`** — see the `customization-patch` skill and `docs/setup/how-to-write-a-patch.md`.
- Adoption (flag 0 → 1) lives only in `patches/adopt_existing_customizations.py` and must stay there.
- Before migrating a client site: `setup/form_snapshot.py` `save` → migrate → `diff`.

Start at `docs/setup/architecture.md`, then `docs/setup/questions-and-answers.md`.

## Accounting patterns (important)

Two doctypes book collateral through the ledger, but differently — don't conflate them:

- **Bank Guarantee-BG** writes **raw `GL Entry` rows** directly. Its tests assert GL rows.
- **Letter of Credit** posts via **system-generated Payment Entry (Internal Transfer)**
  documents, linked by the `letter_of_credit` field and tagged with `is_lc_*` flags. Its
  tests assert those Payment Entries. See `docs/letter-of-credit/reference.md`.

For both, per-company accounts live on **Optima Payment Setting** and are validated as
mandatory before submit. Issue **commission is never reversed** on return/cancel.

## Tests

- `IntegrationTestCase` for suites that save, `UnitTestCase` for ones that write nothing
  (`version-15` still uses `FrappeTestCase`). Integration suites roll back in `tearDown`. No mocking.
- Keep suites that build their own data **out of `doctype/` folders**: on Frappe 16, a test there
  makes Frappe generate test records for the doctype's whole link graph.
- Most suites are live-DB integration tests. Code that keeps its decisions in plain functions
  pairs two files instead: `test_<x>.py` checks those decisions with plain rows and writes
  nothing, and `test_<x>_integration.py` covers only what a real save shows. A matrix case must
  name the plausible bug it catches; one-liners, the code's own constants and message wording get
  none. Example: `overdue_limit/tests/`.
- Build fixtures with the factories in `optima_payment/tests/utils.py`
  (`make_optima_payment_setting`, `make_bank_guarantee_bg`, `make_letter_of_credit`). They
  are defensive and work around this bench's KSA/ZATCA mandatory-field customizations.
- Run: `bench --site <site> run-tests --module optima_payment.tests.test_letter_of_credit`
- CI (`.github/workflows/ci.yml`: Frappe 16 on `develop` and `version-16`, Frappe 15 on
  `version-15`) **auto-discovers every `test_*.py`**
  under the package via `rglob` — new test files need no registration. Some assertions skip
  on sites with extra customizations (e.g. the WTS cost-center rule); CI's `test_site` has
  none, so they run fully there. ERPNext 16 creates no company before tests, so the
  `before_tests` hook (`tests/bootstrap.py`) seeds one on a site that has none. Details in
  `docs/development/testing.md`.

## Docs

`docs/` is the source of truth for how things work. When you change behavior, update the
matching doc. Index: `docs/README.md`.
