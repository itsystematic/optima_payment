
# Copilot Instructions for Optima Payment App

## 🏗️ Architecture Overview
- **Optima Payment** is a Frappe/ERPNext app for managing post-dated cheques, company expenses, and bank guarantee letters, tailored for the Saudi Arabian market.
- Integrates tightly with ERPNext core modules (`Payment Entry`, `Expense Claim`, `Bank Guarantee`, etc.) and overrides key DocType classes and dashboards for custom workflows.
- Uses custom JS for desk/web views and hooks for lifecycle events, permissions, and scheduled tasks.

## 🛠️ Developer Workflows
- **Install**: Use `bench get-app https://github.com/itsystematic/optima_payment.git`, then follow with `bench setup requirements`, `bench build --app optima_payment`, `bench restart`, `bench --site <site> install-app optima_payment`, and `bench --site <site> migrate`.
- **Build**: Always run `bench build --app optima_payment` after JS/CSS changes.
- **Testing**: Validate with ERPNext v15. Use custom scripts and Frappe's test runner for DocType logic.
- **Fixtures**: Roles and permissions are managed via fixtures in `hooks.py`.

## 📦 App-Specific Conventions
- **DocType Overrides**: See `hooks.py` for `override_doctype_class` and `override_doctype_dashboards` (e.g., custom logic for `Expense Claim`, `Payment Entry`, `Bank Guarantee`, and `Purchase Invoice`).
- **Document Events**: Custom handlers for submit/cancel/trash events (see `doc_events` in `hooks.py`).
- **JS Integration**: Desk and list views use custom JS (see `doctype_js`, `doctype_list_js`, `page_js`).
- **Scheduled Tasks**: Daily jobs defined in `scheduler_events`.
- **Jinja Methods**: Custom filters/methods for cheque-related logic.
- **Ignore Links**: `ignore_links_on_delete` prevents accidental deletion of key logs.

## 🔗 Integration Points & Dependencies
- **Required Apps**: Depends on `erpnext` and `frappe` (see `required_apps` in `hooks.py`).
- **External**: YouTube channel for user guides, GitHub for issues/support.
- **Cheque Printing**: 40+ templates, extensible via app settings.
- **Bank Guarantee/Expense Workflows**: Automated journal entries and lifecycle tracking.

## 📝 Key Files & Directories
- `README.md`: Features, install, usage, support.
- `optima_payment/hooks.py`: All Frappe hooks, overrides, events, fixtures, and integration logic.
- `public/js/`: Custom JS for desk, list, and form views.
- `doc_events/`: Python handlers for document lifecycle events.
- `override/`: Custom DocType classes and dashboards.

## ⚡ Example Patterns
- **Cheque Lifecycle**: Customer/supplier cheque flows, rejection handling, reporting.
- **DocType Override**: Custom class for `Payment Entry` to handle cheque logic.
- **Event Hooks**: `on_submit`, `on_cancel`, `on_trash` for `Payment Entry` and `Journal Entry`.
- **Scheduled Task**: Daily job for cheque/guarantee status updates.

---

For unclear or missing sections, please provide feedback to improve these instructions for future AI agents.
