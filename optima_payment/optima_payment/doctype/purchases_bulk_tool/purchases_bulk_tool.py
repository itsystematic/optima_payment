# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from optima_payment.purchases_bulk import vouchers


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

    def validate(self):
        vouchers.set_row_values(self)

    def before_submit(self):
        # Before, not on, submit: the row references stamped here are then saved with the parent.
        vouchers.create_vouchers(self)

    def on_cancel(self):
        vouchers.rollback_vouchers(self)
