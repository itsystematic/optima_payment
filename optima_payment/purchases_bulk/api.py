# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Whitelisted entry points for the Purchases Bulk Tool form."""

import frappe
from frappe import _
from frappe.model.document import Document

from optima_payment.purchases_bulk import vouchers

TOOL = "Purchases Bulk Tool"


@frappe.whitelist()
def get_vat_rate(template: str | None = None) -> float:
    """The template's On Net Total rates summed, in percent, for the amount the grid shows."""
    if not template:
        return 0.0

    frappe.has_permission(vouchers.TEMPLATE, "read", template, throw=True)
    return vouchers.vat_rates([template])[template]


@frappe.whitelist(methods=["POST"])
def update_statuses(tool: str) -> None:
    """Reads each voucher's state back onto the rows of a submitted tool."""
    vouchers.sync_statuses(get_submitted_tool(tool, "read"))


@frappe.whitelist(methods=["POST"])
def run_bulk_action(tool: str, action: str) -> None:
    """Submits, cancels or deletes the vouchers of a submitted tool, all of them or none."""
    if action not in vouchers.BULK_ACTIONS:
        frappe.throw(_("Unknown voucher action {0}.").format(frappe.bold(action)))

    vouchers.run_bulk_action(get_submitted_tool(tool, "submit"), action)


def get_submitted_tool(name: str, permtype: str) -> Document:
    tool = frappe.get_doc(TOOL, name)
    tool.check_permission(permtype)
    if tool.docstatus != 1:
        frappe.throw(_("Submit {0} {1} first.").format(_(TOOL), frappe.bold(name)))
    return tool
