# Changelog

All notable changes to the Optima Payment app will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
