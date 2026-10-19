# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

SAVEPOINT = "purchases_bulk_tool"


class PurchasesBulkTool(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from optima_payment.optima_payment.doctype.purchases_bulk_tool_item.purchases_bulk_tool_item import PurchasesBulkToolItem

        amended_from: DF.Link | None
        auto_submit: DF.Check
        company: DF.Link
        items: DF.Table[PurchasesBulkToolItem]
        posting_date: DF.Date | None
        set_warehouse: DF.Link | None
        voucher_type: DF.Literal["", "Purchase Order", "Purchase Invoice", "Purchase Receipt"]
    # end: auto-generated types

    # ================================================================================================
    # DOCTYPE LIFECYCLE
    # ================================================================================================
    def validate(self):
        self.set_row_values()

    def before_submit(self):
        # Before, not on, submit: the row references stamped here are then saved with the parent.
        self.create_vouchers()

    def on_cancel(self):
        # Must stay in on_cancel: by now the rows are saved with docstatus 2, so each voucher's
        # back-link check no longer sees a submitted row pointing at it and lets it go.
        self.rollback_vouchers()

    # ================================================================================================
    # ROW VALUES
    # ================================================================================================

    def set_row_values(self):
        vat_rates = {vat: get_vat_rate(vat) for vat in {row.vat for row in self.items}}
        for row in self.items:
            row.voucher_posting_date = row.voucher_posting_date or self.posting_date
            row.amount = flt(flt(row.rate) * (1 + vat_rates[row.vat] / 100), row.precision("amount"))

    def group_rows(self):
        """Rows keyed by (supplier, date, VAT template) in first-seen order: one voucher per key,
        because the date and the template both live in the voucher header."""
        groups = {}
        for row in self.items:
            groups.setdefault((row.supplier, getdate(row.voucher_posting_date), row.vat), []).append(row)
        return groups

    # ================================================================================================
    # VOUCHER CREATION
    # ================================================================================================

    def create_vouchers(self):
        # A savepoint, not the request's own rollback, keeps all-or-nothing true for every
        # caller, including bench execute and tests that keep the transaction open.
        frappe.db.savepoint(SAVEPOINT)

        for (supplier, posting_date, vat), rows in self.group_rows().items():
            try:
                voucher = self.make_voucher(supplier, posting_date, vat, rows)
            except (frappe.ValidationError, frappe.PermissionError):
                frappe.db.rollback(save_point=SAVEPOINT)
                frappe.throw(
                    _("Could not create the {0} for supplier {1} dated {2} (rows {3}). No voucher was created.").format(
                        _(self.voucher_type),
                        frappe.bold(supplier),
                        frappe.format(posting_date, "Date"),
                        ", ".join(str(row.idx) for row in rows),
                    )
                )

            status = "Submitted" if voucher.docstatus == 1 else "Draft"
            for row in rows:
                row.reference_doctype = voucher.doctype
                row.reference_name = voucher.name
                row.status = status

    def make_voucher(self, supplier, posting_date, vat, rows) -> Document:
        voucher = frappe.new_doc(self.voucher_type)
        voucher.update(
            {
                "company": self.company,
                "supplier": supplier,
                "taxes_and_charges": vat,
                "ignore_pricing_rule": 1,
            }
        )

        if self.voucher_type == "Purchase Order":
            voucher.transaction_date = posting_date
            voucher.schedule_date = posting_date
        else:
            # Without set_posting_time, validate_posting_time resets posting_date to today.
            voucher.set_posting_time = 1
            voucher.posting_date = posting_date

        if self.set_warehouse and self.voucher_type != "Purchase Invoice":
            voucher.set_warehouse = self.set_warehouse

        for row in rows:
            voucher.append("items", {"item_code": row.item, "qty": 1, "rate": row.rate})

        # ERPNext only copies the template's taxes server-side when an Accounts Settings flag is on.
        voucher.append_taxes_from_master()
        voucher.insert()

        if self.auto_submit:
            voucher.submit()

        return voucher

    # ================================================================================================
    # VOUCHER ROLLBACK
    # ================================================================================================

    def rollback_vouchers(self):
        rows_by_voucher = {}
        for row in self.items:
            if row.reference_name:
                rows_by_voucher.setdefault((row.reference_doctype, row.reference_name), []).append(row)

        for (doctype, name), rows in reversed(rows_by_voucher.items()):
            status = self.rollback_voucher(doctype, name)
            for row in rows:
                row.db_set("status", status, update_modified=False)

    def rollback_voucher(self, doctype, name) -> str:
        voucher = frappe.get_doc(doctype, name)

        if voucher.docstatus == 1:
            voucher.cancel()
            return "Cancelled"

        if voucher.docstatus == 0:
            frappe.delete_doc(doctype, name)
            return "Deleted"

        return "Cancelled"


@frappe.whitelist()
def get_vat_rate(template: str | None = None) -> float:
    """Sum of the On Net Total rates on a Purchase Taxes and Charges Template, in percent."""
    if not template:
        return 0.0

    frappe.has_permission("Purchase Taxes and Charges Template", "read", template, throw=True)
    rates = frappe.get_all(
        "Purchase Taxes and Charges",
        filters={
            "parenttype": "Purchase Taxes and Charges Template",
            "parent": template,
            "charge_type": "On Net Total",
        },
        pluck="rate",
    )
    return sum(flt(rate) for rate in rates)
