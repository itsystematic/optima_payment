import frappe
from frappe import _
from frappe.utils import nowdate
from optima_payment import active_for_company
from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import add_cheque_action_log
from optima_payment.cheque.cases import (
    make_pay_cheque_gl ,
    make_collect_cheque_gl  , 
    make_return_cheque_gl ,
    make_reject_cheque_gl,
    make_deposit_under_collection_gl ,
    make_return_to_holder_gl ,
)



def validate_payment_entry(doc, event) :

    if not doc.get("mode_of_payment") : return

    mode_of_payment_type = frappe.db.get_value("Mode of Payment" , doc.mode_of_payment , "type")

    if mode_of_payment_type != "Cheque" : return

    validate_cheque_no(doc)


def validate_cheque_no(doc) :

    if frappe.db.exists("Payment Entry" , {"reference_no" : doc.reference_no  , "docstatus" : ["!=", 2] }) :
        frappe.throw(_("Reference No. {0} Already Exists").format(frappe.bold(doc.reference_no)))

@active_for_company
def payment_entry_on_submit(doc, event):
    if not doc.get("mode_of_payment"):
        return 

    status = ""
    mode_of_payment = frappe.get_doc("Mode of Payment", doc.mode_of_payment)

    if mode_of_payment.get("type") != "Cheque" : return 
        
    if mode_of_payment.get("is_payable_cheque") == 1 and doc.get("payment_type") == "Pay"  and doc.multi_expense == 0: 
        if doc.get("is_endorsed_cheque") == 1 :
            status = "Issuance From Endorsed"
        else :
            status = "Issuance"
        
    elif mode_of_payment.get("is_receivable_cheque") == 1 and doc.get("payment_type") == "Receive" : 
        status = "For Collection"
        
    if doc.is_endorsed_cheque == 1:
        update_cheque_status(doc.receivable_cheque, "Endorsed")

    doc.db_set("cheque_status", status)
        
def update_cheque_status(name, status, bank_fees_amount=0, posting_date=None):
    
    payment_entry = frappe.get_doc("Payment Entry", name)
    
    payment_entry.db_set("cheque_status", status, update_modified=False)
    
    mode_of_payment = payment_entry.mode_of_payment
    if not posting_date:
        posting_date = frappe.utils.nowdate()
        
    add_cheque_action_log(payment_entry, status, mode_of_payment, bank_fees_amount, posting_date)
    

                
@active_for_company
def payment_entry_on_cancel(doc , event) :
    if doc.get("is_endorsed_cheque") == 1 :
        receivable_cheque = doc.get("receivable_cheque")
        update_cheque_status(receivable_cheque, "For Collection")
    if not doc.get("mode_of_payment")  or not doc.get("pay_mode_of_payment") : return

    mode_of_payment = frappe.get_doc("Mode of Payment" , doc.get("mode_of_payment"))

    if mode_of_payment.get("is_payable_cheque") == 1 or mode_of_payment.get("is_receivable_cheque") == 1 :
        cancel_cheque(doc , nowdate())

    


def cancel_cheque(doc , posting_date = None) :
    cheque_status_logs = frappe.get_all("Cheque Action Log" ,{"payment_entry" : doc.name ,"is_cancelled" : 0} ,["cheque_status" , "bank_fees_amount" , "mode_of_payment"] , order_by="creation desc")
    for cheque_log in cheque_status_logs :
        if cheque_log.get("cheque_status") == "Encashment" : make_pay_cheque_gl(doc , cheque_log.get("mode_of_payment") , posting_date)
        elif cheque_log.get("cheque_status") == "Endorsed" : make_endorsed_cheque_gl(doc ,posting_date)
        elif cheque_log.get("cheque_status") == "Deposit Under Collection" : make_deposit_under_collection_gl(doc , posting_date)
        elif cheque_log.get("cheque_status") == "Collected" : make_collect_cheque_gl(doc, cheque_log.get("mode_of_payment") ,cheque_log.get("bank_fees_amount") , posting_date )
        elif cheque_log.get("cheque_status") == "Rejected" : make_reject_cheque_gl(doc, cheque_log.get("mode_of_payment") ,cheque_log.get("bank_fees_amount") , posting_date )
        elif cheque_log.get("cheque_status") == "Returned" : make_return_cheque_gl(doc, posting_date)
        elif cheque_log.get("cheque_status") == "Return To Holder" : make_return_to_holder_gl(doc ,posting_date)

    frappe.db.set_value("Cheque Action Log" , {"payment_entry" : doc.name} , "is_cancelled" , 1)
    



def payment_entry_on_trash(doc , event) :

    frappe.db.delete("Cheque Action Log" , {"payment_entry" : doc.name})