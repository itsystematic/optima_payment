# Changelog

All notable changes to the Optima Payment app will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
