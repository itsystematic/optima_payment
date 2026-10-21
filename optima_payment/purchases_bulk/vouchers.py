# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Purchases Bulk Tool: grid rows become Purchase Orders, Invoices or Receipts, all of them or none.

The tool only orchestrates. Each voucher is built from plain values and saved through its own
controller, the same path as a voucher made by hand, so ERPNext's rules apply unchanged.

Rows sharing a supplier, date and VAT template become one voucher, because the date and the
template both live in the voucher header. One savepoint wraps the whole run: when a voucher fails,
every voucher made before it in the run is rolled back too. Cancelling the tool undoes its vouchers,
the last created first: submitted ones are cancelled, drafts deleted.

While the tool stays submitted, the bulk actions submit, cancel or delete its vouchers, all or none,
and hooks.py releases the rows' link so a single voucher can also be cancelled or deleted by hand.
However a voucher is deleted, its rows drop the link at once: its name can come back on the next
voucher of its naming series.

Branching lives in the underscore functions, which take plain rows and return values.
"""

from collections import namedtuple

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

TEMPLATE = "Purchase Taxes and Charges Template"
TOOL_ITEM = "Purchases Bulk Tool Item"
PURCHASE_ORDER = "Purchase Order"
PURCHASE_INVOICE = "Purchase Invoice"
SAVEPOINT = "purchases_bulk_tool"

# A rule refusing the voucher, which its message explains. Anything else propagates untouched.
EXPECTED = (frappe.ValidationError, frappe.PermissionError)

DRAFT = "Draft"
SUBMITTED = "Submitted"
CANCELLED = "Cancelled"
DELETED = "Deleted"

SUBMIT = "submit"
CANCEL = "cancel"
DELETE = "delete"
BULK_ACTIONS = (SUBMIT, CANCEL, DELETE)

GroupKey = namedtuple("GroupKey", ["supplier", "posting_date", "vat"])


# ====================================================================================================
# DECISIONS
# Pure: no database.


def _row_amount(qty, rate, vat_rate, precision: int) -> float:
    return flt(flt(qty) * flt(rate) * (1 + flt(vat_rate) / 100), precision)


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
    """The voucher ``rows`` become. ``ignore_pricing_rule`` keeps the rate the user typed.

    An invoice updates stock exactly when the tool names a warehouse, whatever the site's default.
    """
    fields = {
        "company": company,
        "supplier": key.supplier,
        "taxes_and_charges": key.vat,
        "ignore_pricing_rule": 1,
        **_date_fields(voucher_type, key.posting_date),
        "items": [_line(row, set_warehouse) for row in rows],
    }
    if voucher_type == PURCHASE_INVOICE:
        fields["update_stock"] = 1 if set_warehouse else 0
    if set_warehouse:
        fields["set_warehouse"] = set_warehouse
    return fields


def _line(row, set_warehouse: str | None) -> dict:
    """A row's voucher line. Its own warehouse counts only when the tool has one, and then beats it:
    ERPNext fills the header's warehouse only into a blank line."""
    line = {"item_code": row.item, "qty": row.qty, "rate": row.rate}
    if set_warehouse and row.warehouse:
        line["warehouse"] = row.warehouse
    return line


def _voucher_status(docstatus: int | None) -> str:
    """The row status of a voucher at ``docstatus``; None means the voucher no longer exists."""
    return {0: DRAFT, 1: SUBMITTED, 2: CANCELLED, None: DELETED}[docstatus]


def _row_values(status: str) -> dict:
    """What a row holds at ``status``.

    A Deleted row keeps no link. Deleting the newest voucher of a naming series winds its counter
    back (frappe.model.naming.revert_series_if_last), so the next voucher takes the same name and
    a row still holding it would adopt a voucher the tool never made.
    """
    if status == DELETED:
        return {"status": DELETED, "reference_doctype": None, "reference_name": None}
    return {"status": status}


def _rollback_action(docstatus: int | None) -> tuple[str | None, str]:
    """What cancelling the tool does to a voucher, and the status its rows end at."""
    if docstatus == 1:
        return CANCEL, CANCELLED
    if docstatus == 0:
        return DELETE, DELETED
    return None, _voucher_status(docstatus)


def _bulk_step(action: str, docstatus: int | None) -> tuple[bool, str]:
    """Whether a bulk action acts on a voucher at ``docstatus``, and the status its rows end at.

    Submit takes drafts and cancel takes submitted vouchers. Delete takes drafts and cancelled
    vouchers too, which tool cancel keeps.
    """
    if action == SUBMIT and docstatus == 0:
        return True, SUBMITTED
    if action == CANCEL and docstatus == 1:
        return True, CANCELLED
    if action == DELETE and docstatus in (0, 2):
        return True, DELETED
    return False, _voucher_status(docstatus)


def _rows_by_voucher(rows: list) -> list[tuple[tuple[str, str], list]]:
    """Each voucher the rows point at, with those rows, in creation order."""
    by_voucher = {}
    for row in rows:
        if row.reference_name:
            by_voucher.setdefault((row.reference_doctype, row.reference_name), []).append(row)
    return list(by_voucher.items())


def _vouchers_newest_first(rows: list) -> list[tuple[tuple[str, str], list]]:
    return list(reversed(_rows_by_voucher(rows)))


def _bulk_order(action: str, rows: list) -> list[tuple[tuple[str, str], list]]:
    """Submit follows creation order; cancel and delete undo, so they take the last created first."""
    if action == SUBMIT:
        return _rows_by_voucher(rows)
    return _vouchers_newest_first(rows)


def _failure_message(voucher_type: str, key: GroupKey, rows: list) -> str:
    return _("Could not create the {0} for supplier {1} dated {2} (rows {3}). No voucher was created.").format(
        _(voucher_type),
        frappe.bold(key.supplier),
        formatdate(key.posting_date),
        ", ".join(str(row.idx) for row in rows),
    )


def _bulk_failure_message(action: str, doctype: str, name: str, rows: list) -> str:
    message = {
        SUBMIT: _("Could not submit {0} {1} (rows {2}). No voucher was changed."),
        CANCEL: _("Could not cancel {0} {1} (rows {2}). No voucher was changed."),
        DELETE: _("Could not delete {0} {1} (rows {2}). No voucher was changed."),
    }[action]
    return message.format(_(doctype), frappe.bold(name), ", ".join(str(row.idx) for row in rows))


def _nothing_to_do_message(action: str) -> str:
    return {
        SUBMIT: _("No draft voucher to submit."),
        CANCEL: _("No submitted voucher to cancel."),
        DELETE: _("No draft or cancelled voucher to delete."),
    }[action]


# ====================================================================================================
# VALIDATION


def validate_warehouse(tool: Document) -> None:
    """Orders and receipts need the tool's warehouse. Frappe checks mandatory_depends_on only in the
    browser, so the server repeats the rule for imports and API calls."""
    if tool.voucher_type != PURCHASE_INVOICE and not tool.set_warehouse:
        frappe.throw(
            _("{0} is required for a {1}.").format(
                frappe.bold(_(tool.meta.get_label("set_warehouse"))), _(tool.voucher_type)
            ),
            frappe.MandatoryError,
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
        row.amount = _row_amount(row.qty, row.rate, rates.get(row.vat, 0), row.precision("amount"))


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

        status = _voucher_status(voucher.docstatus)
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
    docstatuses = voucher_docstatuses(tool)
    for (doctype, name), rows in _vouchers_newest_first(tool.items):
        action, status = _rollback_action(docstatuses.get(name))
        if action:
            apply_action(action, doctype, name)
        set_status(rows, status)


# ====================================================================================================
# VOUCHER STATUS AND BULK ACTIONS


def voucher_docstatuses(tool: Document) -> dict[str, int]:
    """Voucher name -> docstatus, for every voucher the rows point at. A deleted voucher is absent."""
    names = list({row.reference_name for row in tool.items if row.reference_name})
    if not names:
        return {}

    rows = frappe.get_all(tool.voucher_type, filters={"name": ("in", names)}, fields=["name", "docstatus"])
    return {row.name: row.docstatus for row in rows}


def sync_statuses(tool: Document) -> None:
    """Writes each voucher's current state onto its rows, however the voucher got there."""
    docstatuses = voucher_docstatuses(tool)
    for (_doctype, name), rows in _rows_by_voucher(tool.items):
        set_status(rows, _voucher_status(docstatuses.get(name)))


def run_bulk_action(tool: Document, action: str) -> None:
    """Submits, cancels or deletes every voucher in the state ``action`` takes, all of them or none.

    Every row ends at its voucher's status, including the rows of vouchers the action skips.
    """
    docstatuses = voucher_docstatuses(tool)

    frappe.db.savepoint(SAVEPOINT)
    acted = False
    for (doctype, name), rows in _bulk_order(action, tool.items):
        acts, status = _bulk_step(action, docstatuses.get(name))
        if acts:
            try:
                apply_action(action, doctype, name)
            except EXPECTED:
                frappe.db.rollback(save_point=SAVEPOINT)
                frappe.throw(_bulk_failure_message(action, doctype, name, rows))
            acted = True
        set_status(rows, status)

    if not acted:
        frappe.msgprint(_nothing_to_do_message(action))


def apply_action(action: str, doctype: str, name: str) -> None:
    """Submits, cancels or deletes one voucher through its controller, as the current user."""
    if action == SUBMIT:
        frappe.get_doc(doctype, name).submit()
    elif action == CANCEL:
        frappe.get_doc(doctype, name).cancel()
    elif action == DELETE:
        frappe.delete_doc(doctype, name)


def set_status(rows: list, status: str) -> None:
    values = _row_values(status)
    for row in rows:
        changed = {field: value for field, value in values.items() if row.get(field) != value}
        if changed:
            row.db_set(changed, update_modified=False)


def unlink_tool_rows(voucher: Document, method=None) -> None:
    """after_delete of a Purchase Order, Invoice or Receipt: every tool row pointing at it ends at
    Deleted with no link, before the voucher's name can be given out again."""
    frappe.db.set_value(
        TOOL_ITEM,
        {"reference_doctype": voucher.doctype, "reference_name": voucher.name},
        _row_values(DELETED),
        update_modified=False,
    )
