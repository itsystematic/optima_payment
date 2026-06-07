# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

"""Cheque action log helpers for Payment Entry status transitions."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ChequeActionLog(Document):
    """Read-only audit log for cheque lifecycle actions tied to a Payment Entry."""

    def validate(self):
        self.validate_posting_date()

    def validate_posting_date(self):
        """Keep log entries in chronological order for the same payment entry."""
        cheque_log = frappe.db.get_all(
            self.doctype,
            {
                "payment_entry": self.payment_entry,
                "name": ["!=", self.name],
            },
            ["posting_date"],
            order_by="creation desc",
            limit=1,
        )

        if not cheque_log:
            return

        posting_date = getdate(cheque_log[0].get("posting_date"))
        new_posting_date = getdate(self.posting_date)
        if new_posting_date < posting_date:
            frappe.throw(_("Posting Date should not be earlier than {0}").format(posting_date))


@frappe.whitelist()
def add_cheque_action_log(
    doc,
    cheque_status,
    mode_of_payment=None,
    bank_fees_amount=0.00,
    posting_date=None,
    cost_center=None,
):
    """Create a cheque action log row and mirror the latest status on the Payment Entry."""
    if doc.docstatus == 2:
        return

    cheque_log = frappe.get_doc(
        {
            "doctype": "Cheque Action Log",
            "company": doc.company,
            "payment_entry": doc.name,
            "cheque_status": cheque_status,
            "mode_of_payment": mode_of_payment,
            "bank_fees_amount": bank_fees_amount,
            "posting_date": posting_date,
            "cost_center": cost_center,
        }
    )
    cheque_log.flags.ignore_permissions = True
    cheque_log.flags.ignore_mandatory = True
    cheque_log.save()

    doc.db_set({"cheque_status": cheque_status})
