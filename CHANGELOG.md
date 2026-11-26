# Changelog

All notable changes to the Optima Payment app will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [16.0.0] - 2026-11-26

### Added
- **ERPNext 16**: this line installs on Frappe and ERPNext 16 from `version-16`; ERPNext 15
  sites stay on `version-15` (#14).
- **Statement of Account** (كشف حساب) for customers and suppliers: **Customer Statement** and
  **Supplier Statement** reports, opened from **View ▸ Statement of Account** on the party, list one
  party's vouchers for one company and period with the opening, running and closing balance read
  as DR / CR, and Total Debit, Total Credit and Outstanding Balance cards. Built on the site's
  General Ledger report, whichever app provides it, so its rows and its Opening and Closing rows
  always equal the General Ledger's.
- A **Statement of Account** preview page with Send Email (the PDF attached, logged on the party's
  timeline), Print (Save as PDF from the print window) and Export to Excel. The statement is
  translated and right to left in Arabic, with the company's Arabic name under its name.
- **Time Based Overdue Limit**: rules for a customer or a customer group that warn on save, block
  on save or block on submit of a Sales Invoice or Sales Order once the customer has an invoice
  overdue a set number of days, whatever the customer's balance. Users with an exempt role get the
  warning without the block (#3).
- **Purchases Bulk Tool**: one line per purchase (date, supplier, item, qty, rate, VAT template and
  an optional warehouse). Submitting the tool creates Purchase Orders, Purchase Invoices or Purchase
  Receipts, one per supplier, and its **Vouchers** buttons submit, cancel or delete them in bulk.
  The tool is in the Optima Payment workspace.

### Changed
- The app tells its own custom fields and property setters apart from a site's Customize Form
  changes, and a migrate creates what is missing and updates only its own rows. The
  `adopt_existing_customizations` patch takes ownership of the ones created before, and
  `setup/form_snapshot.py` saves and compares a site's forms around a migrate.
- The role **Optima Payment Manger** is renamed **Optima Payment Manager**; the users and
  permissions that had it keep it.
- The Bank Guarantee override extends ERPNext's own Bank Guarantee controller instead of
  replacing it.
- The tests run on Frappe 16's test classes, and CI runs the whole suite on Frappe 16 (#16).

### Fixed
- The overdue invoice lookup reads a new index on Sales Invoice (#13, #14).
- A blank company on an overdue rule stays blank, so the rule keeps applying to every company.
- A deleted voucher's Purchases Bulk Tool rows are unlinked before its name is reused.
- Statement of Account: the Opening and Closing rows match the site's General Ledger, a zero debit
  or credit is left empty, and the report's columns fill the page.
- The Arabic translations of the Bank Guarantee labels apply again; their rows carried a fieldname
  column that made Frappe read the Arabic as a context.

### Removed
- The obsolete Expense Claim and Expense Claim Type scripts.

## [15.2.0] - 2026-07-06

### Added
- **Bank Guarantee-BG** doctype: Providing/Receiving bank guarantees with Issue, Extend,
  Return, Close, and Re-Open actions, posting raw `GL Entry` rows against the per-company
  accounts configured on Optima Payment Setting. Includes a **Bank Guarantee-BG Report**.
- **Letter of Credit** doctype: Providing/Receiving LCs that book cash-margin collateral via
  system-generated Payment Entries (Internal Transfer), with Extend, Return, Close, and
  Re-Open actions. Includes a **Letter of Credit Report**.
- Tier-4 integration test suites for both doctypes — GL-row assertions for Bank Guarantee,
  generated-Payment-Entry assertions for Letter of Credit — decoupled from site-specific
  (WTS) logic so they run on standard ERPNext; both are auto-discovered by CI via a
  `test_*.py` rglob across the whole package.
- Full documentation overhaul: domain-organized `docs/` (cheque, bank-guarantee,
  letter-of-credit, setup, development) with Mermaid state/flow/entity diagrams,
  accountant/implementer user guides for all three features, a testing guide documenting
  the KSA test-environment assumptions, and an app-level `CLAUDE.md`.
- First-time onboarding checklist in the README (EN/AR) covering the setup required before
  using Bank Guarantees or Letters of Credit.

### Changed
- Cheque Action Log validation refactored for clarity; Payment Entry frontend JS
  modularized; Optima Payment Setting lifecycle hooks reorganized; the setup framework's
  `__init__` orchestration layer was removed in favor of an explicit per-feature file list.
- CI bumped to Node 24-native GitHub Actions.

### Fixed
- Bank Account query filters for providing/receiving Letter of Credit accounts corrected
  (root_type filtering).
- Rename patch made self-contained, removing a dependency on the `banking` module.
- `sync_banking_account_fields` now includes the Bank Guarantee and Letter of Credit
  fields.
- Test factory (`tests/utils.py`) now back-fills Bank Guarantee accounts on a pre-existing
  Optima Payment Setting and satisfies KSA site customizations (Arabic name fields), so the
  Bank Guarantee and Letter of Credit suites run on customized sites.
- Assorted custom-field JSON schema fixes.

## [15.1.1] - 2026-06-04

### Fixed
- **Critical:** Payment Reconciliation now correctly shows payments with NULL `cheque_status` values
  - Previously, non-cheque payments were excluded due to SQL NULL handling in NOT IN clause
  - Added explicit NULL/empty checks before applying cheque status filters
- Fixed per-company activation flag for Optima Payment features
  - Now correctly checks `enable_optima_payment=1` instead of just checking for any setting
- Fixed account-currency GL amount population in cheque transactions
- Fixed mutual exclusivity validation between bank fees and multi-expense features

### Added
- Support for booking advance payments in separate party accounts (`book_advance_payments_in_separate_party_account` field)
- Bank Guarantee account settings in Optima Payment Setting doctype
- Migration patch to move legacy Bank Guarantee account defaults from Company to app settings
- Sync functionality for Mode of Payment bank fees

### Changed
- **Refactor:** Extracted payment entry override logic to dedicated `payment_entry_override.py` module
  - Improved code cohesion and maintainability
  - Separated concerns: GL utilities vs payment reconciliation logic
- **Refactor:** Organized `cheque/utils.py` with clear section dividers for better readability
  - Section 1: General Ledger Entry Creation
  - Section 2: GL Entry Finalization and Reversal
  - Section 3: Number Formatting Utilities
- **Refactor:** Improved docstrings and code clarity across cheque utilities
- **Refactor:** Simplified `should_use_optima_implementation()` logic and error handling
- **Refactor:** Removed redundant field existence checks (now verified upstream)
- Removed obsolete company insurance account fields from Banking settings
- Cleaned up cheque accounts by removing redundant 'reqd' field markers

### Technical Details
- Commits: a7b1c84 through 542600b
- Key files modified:
  - `optima_payment/cheque/payment_entry_override.py` (new)
  - `optima_payment/cheque/utils.py` (refactored)
  - `optima_payment/__init__.py` (updated imports)

## [15.1.0] - (Previous Release)

Initial stable release for ERPNext version 15.
