# Testing

How the automated tests for Optima Payment are written, run locally, and run in CI.

---

## Framework & style

Tests use Frappe's `FrappeTestCase` (unittest-based) and run against a **live site** — they
insert and submit real documents, then assert on the accounting they produce. There is no
mocking. Each test isolates itself with `frappe.db.rollback()` in `tearDown`, so nothing it
creates survives the test.

- **Bank Guarantee-BG** posts raw `GL Entry` rows, so its tests assert GL rows
  (`get_gle` / `validate_gl_entries`).
- **Letter of Credit** posts **Payment Entry (Internal Transfer)** documents, so its tests
  assert on those Payment Entries (`get_lc_payment_entries`, filtered by the `is_lc_*`
  flags). See [letter-of-credit.md](letter-of-credit.md).

---

## Shared fixtures

All test fixtures come from one module: `optima_payment/tests/utils.py`. Import the
factories instead of building documents inline:

| Factory | Builds |
|---------|--------|
| `make_optima_payment_setting(company)` | The per-company Optima Payment Setting with all BG + LC accounts populated (back-fills a pre-existing setting) |
| `make_bank_guarantee_bg(bg_type=…, issue_commission=…, do_not_submit=…)` | A submitted Bank Guarantee with its full dependency chain |
| `make_letter_of_credit(lc_type=…, issue_commission=…, do_not_submit=…, **overrides)` | A submitted Letter of Credit; pass `lc_account=None` to exercise the insurance-account fallback |

The factories are defensive (`get_or_create_*`) and work around this bench's KSA/ZATCA
customizations (mandatory Arabic name fields, tax category, item tax templates, order-level
tax rows). They default to `erpnext.get_default_company()`.

---

## Running locally

Always pass the site you are working on (this bench hosts several):

```bash
# One module (recommended — this is what CI runs)
bench --site <site> run-tests --module optima_payment.optima_payment.doctype.letter_of_credit.test_letter_of_credit
bench --site <site> run-tests --module optima_payment.optima_payment.doctype.bank_guarantee_bg.test_bank_guarantee_bg
```

The site needs `optima_payment` installed and `allow_tests` enabled
(`bench --site <site> set-config allow_tests true`).

### Use `--module`, not `--doctype`

Run these suites with `--module`. The `--doctype "Letter of Credit"` form makes Frappe
auto-generate test records for the doctype's entire link dependency graph, which pulls in
ERPNext's standard fixtures (e.g. `_Test Company`) and fails on a site that doesn't have
that full test dataset:

```
frappe.exceptions.LinkValidationError: Could not find Company: _Test Company
```

Our suites don't use those fixtures — they build their own data with the factories in
`tests/utils.py` against the site's real default company — so `--module` runs them directly
and avoids the dependency machinery.

### Test environment & KSA assumptions

The suites target **standard ERPNext** and are not tied to any customization app. They build
their own data with `create_*`/`make_*`-style factories against the site's real default
company and isolate with `db.rollback()` — the same integration-test pattern ERPNext itself
uses (see `erpnext/accounts/test_utils.py`). A test must never change behaviour based on
whether a specific third-party/customer app is installed.

Because Optima Payment is a **Saudi-first** app, its real (dev and customer) sites carry
KSA/ZATCA doctype-level customizations — e.g. mandatory `customer_name_in_arabic`,
`tax_category`, and item tax templates. The factory helpers in `tests/utils.py` therefore
stay **tolerant** of these: they satisfy the extra mandatory fields when present and fall
back gracefully when absent (unknown keys are dropped; missing groups fall back). This is
deliberate — the *same* suite then runs on a clean CI site **and** on a customized KSA site,
which is the environment the app actually ships into. Do not strip these workarounds to
"purify" the factory: that would leave a suite that only runs on vanilla ERPNext, the
environment least like production.

On a clean CI site (erpnext + optima_payment only) these KSA paths are **inert** rather than
exercised. If you want CI to mirror production and genuinely exercise them, install
`optima_zatca` (and any other KSA customization apps) in `.github/workflows/ci.yml` so the
mandatory-field paths are hit for real. Until then, treat the KSA branches in the factory as
covered only on real sites. See the `TODO` block in `test_letter_of_credit.py`.

---

## Continuous integration

CI is defined in `.github/workflows/ci.yml` and runs on every push / pull request against
`version-15`. It spins up MariaDB + Redis, installs `erpnext` + `optima_payment` on a fresh
`test_site`, enables tests, and then **auto-discovers every `test_*.py` under the
`optima_payment/` package** via `rglob`, running `bench run-tests --module …` for each.

**You do not need to register new test files anywhere** — dropping a
`test_<something>.py` under the package (including doctype-local `…/doctype/<x>/test_<x>.py`)
is enough for CI to pick it up on the next run.
