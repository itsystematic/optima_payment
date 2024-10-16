# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class ChequeActionLog(Document):
    
    def validate(self) :
        self.validate_posting_date()

    def validate_posting_date(self) :

        cheque_log = frappe.db.get_all(self.doctype , {
                "payment_entry" : self.payment_entry ,
                "name" :["!=" , self.name ]
            } , 
            ["posting_date"],
            order_by="creation desc",
            limit=1
        )

        if cheque_log :
            posting_date = getdate(cheque_log[0].get("posting_date"))
            new_posting_date = getdate(self.posting_date)
            if new_posting_date < posting_date :
                frappe.throw(_("Posting Date should be greater than {0}").format(posting_date))



@frappe.whitelist()
def add_cheque_action_log(doc , cheque_status , mode_of_payment=None , bank_fees_amount =0.00, posting_date = None) :

    if doc.docstatus == 2 : return 
    
    cheque_log = frappe.get_doc({
        "doctype": "Cheque Action Log",
        "company" : doc.company ,
        "payment_entry": doc.name,
        "cheque_status": cheque_status,
        "mode_of_payment": mode_of_payment,
        "bank_fees_amount": bank_fees_amount,
        "posting_date": posting_date
    })
    cheque_log.flags.ignore_permissions = True
    cheque_log.flags.ignore_mandatory = True
    cheque_log.save()


    fields_updated = {"cheque_status" : cheque_status }

    if mode_of_payment and doc.docstatus == 1 : fields_updated["pay_mode_of_payment"] = mode_of_payment
    if bank_fees_amount and doc.docstatus == 1 : fields_updated["bank_fees_amount"] = bank_fees_amount

    doc.db_set(fields_updated)



# @frappe.whitelist()
# def add_cheque_action_log(cheque_action_details):
#     """Add a log entry for a cheque action using details from a dictionary."""
#     doc = cheque_action_details["doc"]
#     # cheque_status = cheque_action_details["cheque_status"]
#     # mode_of_payment = cheque_action_details.get("mode_of_payment")
#     # bank_fees_amount = cheque_action_details.get("bank_fees_amount", 0.00)

#     frappe.get_doc({
#         "doctype": "Cheque Action Log",
#         "payment_entry": doc.name,
#         "cheque_status": cheque_action_details.get("cheque_status"),
#         "mode_of_payment": cheque_action_details.get("mode_of_payment"),
#         "bank_fees_amount": cheque_action_details.get("bank_fees_amount", 0.00)
#     }).insert(ignore_mandatory=True, ignore_permissions=True, ignore_links=True)

#     fields_updated = {"cheque_status": cheque_status}

#     if mode_of_payment and doc.docstatus == 1:
#         fields_updated["pay_mode_of_payment"] = mode_of_payment
#     if bank_fees_amount and doc.docstatus == 1:
#         fields_updated["bank_fees_amount"] = bank_fees_amount

#     doc.db_set(fields_updated)