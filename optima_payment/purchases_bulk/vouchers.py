# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Purchases Bulk Tool: grid rows become Purchase Orders, Invoices or Receipts, all of them or none.

The tool only orchestrates. Each voucher is built from plain values and saved through its own
controller, the same path as a voucher made by hand, so ERPNext's rules apply unchanged.

Rows sharing a supplier, date and VAT template become one voucher, because the date and the
template both live in the voucher header. One savepoint wraps the whole run: when a voucher fails,
every voucher made before it in the run is rolled back too. Cancelling the tool undoes its vouchers,
the last created first: submitted ones are cancelled, drafts deleted.

Branching lives in the underscore functions, which take plain rows and return values.
"""

from collections import namedtuple

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

TEMPLATE = "Purchase Taxes and Charges Template"
PURCHASE_ORDER = "Purchase Order"
PURCHASE_INVOICE = "Purchase Invoice"
SAVEPOINT = "purchases_bulk_tool"

# A rule refusing the voucher, which its message explains. Anything else propagates untouched.
EXPECTED = (frappe.ValidationError, frappe.PermissionError)

DRAFT = "Draft"
SUBMITTED = "Submitted"
CANCELLED = "Cancelled"
DELETED = "Deleted"

CANCEL = "cancel"
DELETE = "delete"

GroupKey = namedtuple("GroupKey", ["supplier", "posting_date", "vat"])


# ====================================================================================================
# DECISIONS
# Pure: no database.


def _row_amount(rate, vat_rate, precision: int) -> float:
    return flt(flt(rate) * (1 + flt(vat_rate) / 100), precision)


def _group_rows(rows: list) -> dict[GroupKey, list]:
    """The rows of each voucher, keyed by what its header holds, in first-seen order."""
    groups = {}
    for row in rows:
        key = GroupKey(row.supplier, getdate(row.voucher_posting_date), row.vat)
        groups.setdefault(key, []).append(row)
    return groups


def _date_fields(voucher_type: str, posting_date) -> dict:
    if voucher_type == PURCHASE_ORDER:
        return {"transaction_date": posting_date, "schedule_date": posting_date}
    # Without set_posting_time, validate_posting_time resets posting_date to today.
    return {"set_posting_time": 1, "posting_date": posting_date}


def _voucher_fields(voucher_type: str, company: str, set_warehouse: str | None, key: GroupKey, rows: list) -> dict:
    """The voucher ``rows`` become. ``ignore_pricing_rule`` keeps the rate the user typed."""
    fields = {
        "company": company,
        "supplier": key.supplier,
        "taxes_and_charges": key.vat,
        "ignore_pricing_rule": 1,
        **_date_fields(voucher_type, key.posting_date),
        "items": [{"item_code": row.item, "qty": 1, "rate": row.rate} for row in rows],
    }
    if set_warehouse and voucher_type != PURCHASE_INVOICE:
        fields["set_warehouse"] = set_warehouse
    return fields


def _created_status(docstatus: int) -> str:
    return SUBMITTED if docstatus == 1 else DRAFT


def _rollback_action(docstatus: int | None) -> tuple[str | None, str]:
    """What cancelling the tool does to a voucher, and the status its rows end at."""
    if docstatus == 1:
        return CANCEL, CANCELLED
    if docstatus == 0:
        return DELETE, DELETED
    if docstatus is None:
        return None, DELETED
    return None, CANCELLED


def _vouchers_newest_first(rows: list) -> list[tuple[tuple[str, str], list]]:
    """Each voucher the rows point at, with those rows, the last created first."""
    by_voucher = {}
    for row in rows:
        if row.reference_name:
            by_voucher.setdefault((row.reference_doctype, row.reference_name), []).append(row)
    return list(reversed(by_voucher.items()))


def _failure_message(voucher_type: str, key: GroupKey, rows: list) -> str:
    return _("Could not create the {0} for supplier {1} dated {2} (rows {3}). No voucher was created.").format(
        _(voucher_type),
        frappe.bold(key.supplier),
        formatdate(key.posting_date),
        ", ".join(str(row.idx) for row in rows),
    )


# ====================================================================================================
# ROW VALUES


def vat_rates(templates) -> dict[str, float]:
    """Template -> the sum of its On Net Total rates, in percent. Blank templates are skipped."""
    templates = {template for template in templates if template}
    if not templates:
        return {}

    rows = frappe.get_all(
        "Purchase Taxes and Charges",
        filters={"parenttype": TEMPLATE, "parent": ("in", list(templates)), "charge_type": "On Net Total"},
        fields=["parent", "rate"],
    )
    rates = dict.fromkeys(templates, 0.0)
    for row in rows:
        rates[row.parent] += flt(row.rate)
    return rates


def set_row_values(tool: Document) -> None:
    """Fills a blank row date from the tool's posting date and sets each row's rate-plus-VAT amount."""
    rates = vat_rates(row.vat for row in tool.items)
    for row in tool.items:
        row.voucher_posting_date = row.voucher_posting_date or tool.posting_date
        row.amount = _row_amount(row.rate, rates.get(row.vat, 0), row.precision("amount"))


# ====================================================================================================
# VOUCHER CREATION


def create_vouchers(tool: Document) -> None:
    """One voucher per group of rows, all or none, each row stamped with the voucher it went into."""
    # A savepoint, not the request's own rollback, keeps all-or-nothing true for every caller,
    # including bench execute and tests that keep the transaction open.
    frappe.db.savepoint(SAVEPOINT)

    for key, rows in _group_rows(tool.items).items():
        fields = _voucher_fields(tool.voucher_type, tool.company, tool.set_warehouse, key, rows)
        try:
            voucher = make_voucher(tool.voucher_type, fields, submit=tool.auto_submit)
        except EXPECTED:
            frappe.db.rollback(save_point=SAVEPOINT)
            frappe.throw(_failure_message(tool.voucher_type, key, rows))

        status = _created_status(voucher.docstatus)
        for row in rows:
            row.update({"reference_doctype": voucher.doctype, "reference_name": voucher.name, "status": status})


def make_voucher(voucher_type: str, fields: dict, *, submit: bool) -> Document:
    voucher = frappe.new_doc(voucher_type)
    voucher.update(fields)
    # ERPNext only copies the template's taxes server-side when an Accounts Settings flag is on.
    voucher.append_taxes_from_master()
    voucher.insert()

    if submit:
        voucher.submit()

    return voucher


# ====================================================================================================
# VOUCHER ROLLBACK


def rollback_vouchers(tool: Document) -> None:
    """Cancels the tool's submitted vouchers and deletes its drafts, the last created first."""
    for (doctype, name), rows in _vouchers_newest_first(tool.items):
        action, status = _rollback_action(frappe.db.get_value(doctype, name, "docstatus"))
        if action == CANCEL:
            frappe.get_doc(doctype, name).cancel()
        elif action == DELETE:
            frappe.delete_doc(doctype, name)

        for row in rows:
            row.db_set("status", status, update_modified=False)
