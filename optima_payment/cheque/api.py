import frappe
from frappe import _
from optima_payment.cheque.utils import create_jv_for_return_to_holder
from optima_payment.cheque.cases import (
    make_pay_cheque_gl ,
    make_collect_cheque_gl , 
    make_return_cheque_gl ,
    make_endorsed_cheque_gl ,
    make_deposit_under_collection_gl ,
    make_reject_cheque_gl ,
    make_return_to_holder_gl
)

@frappe.whitelist()
def pay_cheque(posting_date , docname , mode_of_payment) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_pay_cheque_gl(payment_entry , mode_of_payment , posting_date)

@frappe.whitelist() 
def collect_cheque(posting_date , docname , has_bank_fees , mode_of_payment , bank_fees_amount) :

    payment_entry = frappe.get_doc("Payment Entry", docname)
    bank_fees_amount = float(bank_fees_amount) if has_bank_fees == "1" else 0.0
    make_collect_cheque_gl(payment_entry, mode_of_payment ,bank_fees_amount , posting_date)


@frappe.whitelist()
def return_cheque(docname , posting_date , remarks) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_return_cheque_gl(payment_entry, posting_date , remarks)


@frappe.whitelist()
def reject_cheque(docname , posting_date ,remarks , mode_of_payment=None , has_bank_fees=None ,bank_fees_amount=None ) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    bank_fees_amount = float(bank_fees_amount) if has_bank_fees == "1" else 0.0
    make_reject_cheque_gl(payment_entry, mode_of_payment, bank_fees_amount , posting_date , remarks)
    

@frappe.whitelist()
def redeposit_cheque(docname):
    payment_entry = frappe.get_doc("Payment Entry", docname)
    payment_entry.db_set("cheque_status" , "For Collection")


@frappe.whitelist()
def return_to_holder(docname, posting_date, remarks):
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_return_to_holder_gl(payment_entry, posting_date, remarks)


@frappe.whitelist()
def endorsed_cheque(docname , cheque_no , posting_date) :

    payment_entry = frappe.get_doc("Payment Entry", docname)
    against_payment_entry = frappe.get_doc("Payment Entry", cheque_no )
    make_endorsed_cheque_gl(payment_entry , against_payment_entry , posting_date)
    

@frappe.whitelist()
def deposit_under_collection(docname , posting_date) :

    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_deposit_under_collection_gl(payment_entry, posting_date)



# 
@frappe.whitelist()
def get_receivable_cheque(name) :

    return frappe.db.get_values("Payment Entry" , name , [
            "paid_amount", 
            "reference_no", 
            "reference_date", 
            "bank_name", 
            "beneficiary_name", 
            "received_amount",
            "paid_to as paid_from"
        ] ,as_dict=True
    )


@frappe.whitelist()
def get_company_settings(company) :
    company_settings = {"enable_optima_payment" : 0}

    if optima_payment_settings:= frappe.db.exists("Optima Payment Setting" , {"company" : company , "enable_optima_payment" : 1}) :
        company_settings = frappe.get_doc("Optima Payment Setting" , optima_payment_settings)

    return company_settings