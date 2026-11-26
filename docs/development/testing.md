# Testing

How the automated tests for Optima Payment are written, run locally, and run in CI.

---

## Framework & style

Tests use Frappe 16's `IntegrationTestCase` and run against a **live site** — they insert and
submit real documents, then assert on the accounting they produce. There is no mocking. Each
test isolates itself with `frappe.db.rollback()` in `tearDown`, so nothing it creates survives
the test. Suites that write nothing (the matrix files below) use `UnitTestCase`. `version-15`
keeps `FrappeTestCase`, the only class Frappe 15 has, so a backported test may need its base
class changed.

Suites that build their own data live **outside `doctype/` folders**, in `optima_payment/tests/`
or the feature's own `tests/` folder. Frappe 16 generates test records for a test module inside
`doctype/<x>/`: every record type the doctype links to, then everything those link to. That
walk pulls in ERPNext's `_Test Company` fixtures and fails on doctypes ERPNext 16 no longer
ships, such as `Payment Gateway`. A mocked test that writes nothing (`UnitTestCase`) can stay
beside its doctype, because `UnitTestCase` generates no records.

- **Bank Guarantee-BG** posts raw `GL Entry` rows, so its tests assert GL rows
  (`get_gle` / `validate_gl_entries`).
- **Letter of Credit** posts **Payment Entry (Internal Transfer)** documents, so its tests
  assert on those Payment Entries (`get_lc_payment_entries`, filtered by the `is_lc_*`
  flags). See [letter-of-credit/reference.md](../letter-of-credit/reference.md).
- **Purchases Bulk Tool** keeps its decisions in plain functions, so its tests come as a pair.
  `test_vouchers.py` checks those decisions with plain rows and writes nothing; it runs in
  milliseconds and needs no data on the site. `test_vouchers_integration.py` asserts on the real
  vouchers (lines, header dates, docstatus) and the row status / reference stamps. See
  [purchases-bulk-tool/reference.md](../purchases-bulk-tool/reference.md).
- **Time Based Overdue Limit** pairs the same way. `test_limit.py` runs the rule precedence and how
  triggered rules combine on plain rules; `test_limit_integration.py` saves and submits real Sales
  Invoices and Sales Orders for a customer with an invoice 25 days overdue. See
  [overdue-limit/reference.md](../overdue-limit/reference.md).

A matrix case earns its place by naming the plausible bug it catches: how rules combine, a
boundary, a reachable edge case, or a spec table from the docs. A one-liner, a loop over the code's
own constant, and a message's wording get no case; assert which line a branch produces, not the
sentence. `overdue_limit/tests/test_limit.py` is the worked example.

---

## Shared fixtures

All test fixtures come from one module: `optima_payment/tests/utils.py`. Import the
factories instead of building documents inline:

| Factory | Builds |
|---------|--------|
| `make_optima_payment_setting(company)` | The per-company Optima Payment Setting with all BG + LC accounts populated (back-fills a pre-existing setting) |
| `make_bank_guarantee_bg(bg_type=…, issue_commission=…, do_not_submit=…)` | A submitted Bank Guarantee with its full dependency chain |
| `make_letter_of_credit(lc_type=…, issue_commission=…, do_not_submit=…, **overrides)` | A submitted Letter of Credit; pass `lc_account=None` to exercise the insurance-account fallback |
| `make_purchases_bulk_tool(voucher_type=…, rows=…, auto_submit=…, do_not_submit=…, **overrides)` | A submitted Purchases Bulk Tool; each `rows` dict overrides only the keys it names (supplier, item, rate, vat, voucher_posting_date, and qty or warehouse, which default to 1 and blank) |
| `get_or_create_warehouse(company, warehouse_name)` | A leaf Warehouse of the company under one of its warehouse groups, for tests that need more than one |
| `get_or_create_purchase_taxes_template(company)` | A Purchase Taxes and Charges Template with one On Net Total row on the suite's own VAT account at `PURCHASE_VAT_RATE`, exclusive of the rate (`included_in_print_rate: 0`, whatever the site's default), with a cost center |
| `get_or_create_purchase_item(company, item_code, is_stock_item=…)` | A purchase Item taxed by the suite's own Item Tax Template, its tax row carrying the test suppliers' tax category so that template applies; pass `is_stock_item=1` for Purchase Receipt tests |
| `get_or_create_purchase_item_tax_template(company)` | The Item Tax Template behind those items, on the same account and rate |
| `set_test_cost_center_default(company)` | Makes a leaf cost center the session user's `cost_center` default, so the tool's vouchers carry one on sites that make it mandatory on Purchase Invoice. It lives in the defaults cache: pair it with `frappe.clear_cache(user=frappe.session.user)` after the rollback |
| `get_or_create_sales_item_tax_template(company)` | The Item Tax Template on the test item behind every Sales Order, Purchase Order and Sales Invoice line: one row at `SALES_VAT_RATE` on the suite's own sales VAT account. The order's pre-seeded tax row reads the item's own template, so a fresh site needs no template of its own |
| `make_sales_order(customer=…, do_not_insert=…, do_not_submit=…, **overrides)` | A one-line Sales Order on the test item, cost center and pre-seeded tax row; `make_reference_sales_order` wraps it |
| `make_sales_invoice(customer=…, posting_date=…, due_date=…, do_not_insert=…, do_not_submit=…, **overrides)` | A one-line Sales Invoice; a past `posting_date` is kept, and the due date defaults to it. The header has no cost center, as on real invoices, because a payment copies it onto balance sheet lines that some sites refuse one on |
| `make_invoice_overdue(invoice, days)` | Moves the invoice's due date and payment schedule `days` into the past, then runs ERPNext's `update_invoice_status` so the invoice turns Overdue as it would on a live site |
| `make_credit_note(invoice)` | An unsaved full return of the invoice, with the return reason some sites require |
| `make_invoice_payment(invoice, allocate=…)` | A submitted Payment Entry for the invoice's outstanding amount; `allocate=False` leaves it unallocated, so the invoice stays outstanding while the customer owes nothing |
| `make_overdue_limit(party=…, action=…, threshold_days=…, applies_to=…, company=…, exempt_roles=…, enabled=…)` | A Time Based Overdue Limit rule |

The factories are defensive (`get_or_create_*`) and work around this bench's KSA/ZATCA
customizations (mandatory Arabic name fields, tax category, item tax templates, order-level
tax rows). They default to `erpnext.get_default_company()`.

---

## Running locally

Always pass the site you are working on (this bench hosts several):

```bash
# One module (recommended — this is what CI runs)
bench --site <site> run-tests --module optima_payment.tests.test_letter_of_credit
bench --site <site> run-tests --module optima_payment.tests.test_bank_guarantee_bg
bench --site <site> run-tests --module optima_payment.purchases_bulk.tests.test_vouchers
bench --site <site> run-tests --module optima_payment.purchases_bulk.tests.test_vouchers_integration
bench --site <site> run-tests --module optima_payment.overdue_limit.tests.test_limit
bench --site <site> run-tests --module optima_payment.overdue_limit.tests.test_limit_integration
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

CI is defined in `.github/workflows/ci.yml`, which each branch keeps for itself: `develop` and
`version-16` run against Frappe/ERPNext 16, `version-15` against 15. It spins up MariaDB +
Redis, installs `erpnext` + `optima_payment` on a fresh `test_site`, enables tests, and then
**auto-discovers every `test_*.py` under the `optima_payment/` package** via `rglob`, running
`bench run-tests --module …` for each. The run lists every module that failed, not just the first.

ERPNext 16 no longer runs the setup wizard before tests, so a fresh v16 site has no company. The
app's own `before_tests` hook, `optima_payment/tests/bootstrap.py`, creates **Optima Payment Test
Company** (Saudi Arabia, SAR) on a site without one and leaves any other site untouched. On
`version-15`, ERPNext's own hook still creates the CI company.

**You do not need to register new test files anywhere** — dropping a
`test_<something>.py` anywhere under the package is enough for CI to pick it up on the next run.
