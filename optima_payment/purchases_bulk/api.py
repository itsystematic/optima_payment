# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Whitelisted entry points for the Purchases Bulk Tool form."""

import frappe

from optima_payment.purchases_bulk.vouchers import TEMPLATE, vat_rates


@frappe.whitelist()
def get_vat_rate(template: str | None = None) -> float:
    """The template's On Net Total rates summed, in percent, for the amount the grid shows."""
    if not template:
        return 0.0

    frappe.has_permission(TEMPLATE, "read", template, throw=True)
    return vat_rates([template])[template]
