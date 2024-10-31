import frappe
from frappe import _
from optima_payment.cheque.cases import (
    make_pay_cheque_gl ,
    make_collect_cheque_gl , 
    make_return_cheque_gl ,
    make_deposit_under_collection_gl ,
    make_reject_cheque_gl ,
    make_return_to_holder_gl
)

@frappe.whitelist()
def pay_cheque(posting_date , docname , mode_of_payment) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_pay_cheque_gl(payment_entry , mode_of_payment , posting_date)

@frappe.whitelist() 
def collect_cheque(posting_date , docname , cost_center,has_bank_commissions , mode_of_payment , bank_fees_commission=None) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    bank_fees_commission = float(bank_fees_commission) if has_bank_commissions == "1" else 0.0
    make_collect_cheque_gl(payment_entry, mode_of_payment ,bank_fees_commission , posting_date,cost_center)


@frappe.whitelist()
def return_cheque(docname , posting_date , remarks) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_return_cheque_gl(payment_entry, posting_date , remarks)


@frappe.whitelist()
def reject_cheque(docname , posting_date ,remarks ,cost_center, mode_of_payment=None , has_bank_fees=None ,bank_fees_amount=None ) :
    payment_entry = frappe.get_doc("Payment Entry", docname)
    bank_fees_amount = float(bank_fees_amount) if has_bank_fees == "1" else 0.0
    make_reject_cheque_gl(payment_entry, mode_of_payment, bank_fees_amount , posting_date ,cost_center, remarks)
    if payment_entry.cheque_deposit_slip :
        payment_entry.db_set("cheque_deposit_slip" , None)
    

@frappe.whitelist()
def redeposit_cheque(docname):
    payment_entry = frappe.get_doc("Payment Entry", docname)
    payment_entry.db_set("cheque_status" , "For Collection")


@frappe.whitelist()
def return_to_holder(docname, posting_date, remarks):
    payment_entry = frappe.get_doc("Payment Entry", docname)
    make_return_to_holder_gl(payment_entry, posting_date, remarks)
    if payment_entry.cheque_deposit_slip :
        payment_entry.db_set("cheque_deposit_slip" , None)


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
            "received_amount",
            "paid_to as paid_from",
            "payee_name",
        ] ,as_dict=True
    )


@frappe.whitelist()
def get_company_settings(company) :
    company_settings = {"enable_optima_payment" : 0}

    if optima_payment_settings:= frappe.db.exists("Optima Payment Setting" , {"company" : company , "enable_optima_payment" : 1}) :
        company_settings = frappe.get_doc("Optima Payment Setting" , optima_payment_settings)

    return company_settings



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mode_of_payment(doctype, txt, searchfield, start, page_len, filters):
    
    conditions = ""
    
    if txt : conditions += f"AND mof.name LIKE '{txt}' "

    if filters.get("company") : conditions += f"AND mofa.company = '{filters.get('company')}' "
    if filters.get("default_currency") : conditions += f"AND ac.account_currency = '{filters.get('default_currency')}' "

    if filters.get("type") : 
        conditions += f"AND mof.type IN {tuple(filters.get('type')[1])} " if type(filters.get("type")) == list else f"AND mof.type = '{filters.get('type')}' "

    return frappe.db.sql("""
        SELECT mof.name , mofa.default_account , ac.account_currency
        FROM `tabMode of Payment` mof
        INNER JOIN `tabMode of Payment Account` mofa ON mof.name = mofa.parent
        LEFT JOIN `tabAccount` ac ON ac.name = mofa.default_account
        WHERE mof.enabled = 1
            {conditions}
    """.format(conditions = conditions))