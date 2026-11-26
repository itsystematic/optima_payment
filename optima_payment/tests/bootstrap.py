"""Seed the site the app's integration tests run on.

ERPNext 16 no longer completes the setup wizard before tests, so a fresh test site has no
company, and every factory in `tests/utils.py` falls back to `erpnext.get_default_company()`.
This gives such a site a Saudi company, the market the app ships into.

A site that already has a company is left untouched.
"""

import frappe
from erpnext.setup.utils import enable_all_roles_and_domains
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.utils import now_datetime

TEST_COMPANY = "Optima Payment Test Company"


def before_tests():
    if frappe.db.a_row_exists("Company"):
        return

    frappe.clear_cache()
    setup_complete(setup_wizard_args(now_datetime().year))
    # setup_complete returns early on a site already marked complete.
    if not frappe.db.a_row_exists("Company"):
        raise RuntimeError(f"The setup wizard finished without creating {TEST_COMPANY}; see the Error Log.")

    enable_all_roles_and_domains()
    frappe.db.commit()


def setup_wizard_args(year):
    return {
        "company_name": TEST_COMPANY,
        "company_abbr": "OPT",
        "country": "Saudi Arabia",
        "currency": "SAR",
        "timezone": "Asia/Riyadh",
        "language": "english",
        "chart_of_accounts": "Standard",
        "fy_start_date": f"{year}-01-01",
        "fy_end_date": f"{year}-12-31",
    }
