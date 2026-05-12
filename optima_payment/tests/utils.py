"""Shared test helpers for Optima Payment."""

import frappe
import erpnext
from frappe.utils import nowdate

from optima_payment.override.doctype_class.payment_entry import CustomPaymentEntry


def get_payment_entry_naming_series() -> str:
    """Return the default naming series used by Payment Entry tests."""
    return frappe.get_meta("Payment Entry").get_field("naming_series").default or "PAY-.FY.-"


def get_payment_entry_account(company: str | None = None) -> str:
    """Pick a bank or cash account that Payment Entry is allowed to use."""
    company = company or erpnext.get_default_company()
    account = frappe.get_list(
        "Account",
        filters={"company": company, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0},
        pluck="name",
        reference_doctype="Payment Entry",
        limit=1,
    )

    if not account:
        frappe.throw(f"No bank or cash account is permitted for Payment Entry in company {company}")

    return account[0]


def make_payment_entry(
    *,
    multi_expense: int = 0,
    company: str | None = None,
    payment_account: str | None = None,
    naming_series: str | None = None,
) -> CustomPaymentEntry:
    """Build a minimal Payment Entry document for override-focused tests."""
    company = company or erpnext.get_default_company()
    payment_account = payment_account or get_payment_entry_account(company)
    naming_series = naming_series or get_payment_entry_naming_series()

    pe = frappe.new_doc("Payment Entry")
    pe.update(
        {
            "naming_series": naming_series,
            "payment_type": "Pay",
            "posting_date": nowdate(),
            "company": company,
            "multi_expense": multi_expense,
            "paid_from": payment_account,
            "paid_amount": 100,
            "received_amount": 100,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "base_paid_amount": 100,
            "base_received_amount": 100,
        }
    )
    return pe
