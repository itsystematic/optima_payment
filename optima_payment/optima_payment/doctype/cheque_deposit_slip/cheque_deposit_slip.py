# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _ 
from frappe.model.document import Document
from optima_payment.cheque.cases import make_cheque_slip_gl

class ChequeDepositSlip(Document):
    
    def validate(self) :
        self.validate_company()
        self.validate_payment_entry()


    def validate_company(self) :

        if not frappe.db.exists("Optima Payment Setting" , {"company" : self.company , "enable_optima_payment" : 1 }) :
            frappe.throw(_("Yout Must Enable in Optima Payment Setting For This Company {0}").format(self.company)) 


    def validate_payment_entry(self) :

        for item in self.cheque_deposit_slip_items :
            payment_entry_doc = frappe.get_doc("Payment Entry" , item.get("payment_entry")) 

            if payment_entry_doc.get("cheque_status") != "For Collection" :
                frappe.throw(_("You Must Remove cheque {0} in row {1}").format(frappe.bold(item.get("payment_entry")) ,frappe.bold(item.get("idx"))))
        
            if payment_entry_doc.get("docstatus") != 1 :
                frappe.throw(_("Cheque is Cancelled"))

            if payment_entry_doc.get("payment_type") != "Receive" :
                frappe.throw(_("Cheque Must be Receive"))

    

    def on_submit(self) :

        self.validate()
        # self.make_payment_entry_gl(reverse=False)
        # self.update_cheque_status("Deposited")


    def make_payment_entry_gl(self , reverse) :

        for row in self.cheque_deposit_slip_items :
            doc = frappe.get_doc("Payment Entry" , row.get("payment_entry"))
            make_cheque_slip_gl(doc , reverse=reverse)


    def update_cheque_status(self , status) :

        names = list(map(lambda x : x.get("payment_entry") , self.cheque_deposit_slip_items))
        pe = frappe.qb.DocType("Payment Entry")
        frappe.qb.update(pe).set(pe.cheque_status, status).set(pe.from_slip, 1 if self.docstatus == 1 else 0).where( (pe.name.isin(names)) ).run()


    # def on_cancel(self) :
        # self.make_payment_entry_gl(reverse=True)
        # self.update_cheque_status("To Collection")


@frappe.whitelist()
def get_payment_entry_details(payment_entry) :

    if not payment_entry : return {}

    return frappe.db.get_value("Payment Entry" , payment_entry , ['reference_no' , 'reference_date' , 'paid_amount' , 'paid_to' , "cost_center"] ,as_dict=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payment_entries(doctype, txt, searchfield, start, page_len, filters):

    conditions = ""

    if filters.get("company") :
        conditions += "AND company = '{0}' ".format(filters.get("company"))

    if filters.get("names") :
        items_tule = tuple(filters.get("names"))
        conditions += "AND name NOT IN {0}  ".format( items_tule if len(items_tule) > 1 else f"('{items_tule[0]}')" )

    conditions += "AND reference_no LIKE %(txt)s " if txt else ""

    sql_query =  frappe.db.sql("""
        SELECT 
            name, reference_no 
        FROM `tabPayment Entry` 
        WHERE docstatus = 1 
            AND payment_type = "Receive" 
            AND cheque_status = "Deposit Under Collection"
            {conditions}
    """.format(conditions=conditions), 
    {
        'txt': "%{}%".format(txt),
    })


    return sql_query