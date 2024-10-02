import frappe
from frappe.utils import today
from optima_payment import get_applicable_campanies_optima_payment
from optima_payment.cheque.cases import make_pay_cheque_gl , make_deposit_under_collection_gl

def optima_payment_daily() :
    """ Scheduler Run IF Enable Scheduler In Optima Payment Setting Per Company"""

    list_of_optima_payment = get_applicable_campanies_optima_payment()
    run_scheduler(list_of_optima_payment)
    
    # Clear Cache For Payment Entry
    frappe.clear_cache(doctype="Payment Entry")


def run_scheduler(list_of_optima_payment:list) -> None :

    for optima_payment_setting in list_of_optima_payment : 

        auto_pay_cheque_in_time(optima_payment_setting)
        auto_deposit_under_collection_in_time(optima_payment_setting)

def auto_pay_cheque_in_time(optima_payment_setting) :

    if not optima_payment_setting.enable_auto_pay_cheque_in_time : return 

    conditions = {
        "payment_type"  :"Pay" ,
        "docstatus" : 1 ,
        "cheque_status" : "Issuance" ,
        "reference_date" : today(),
        "company" : optima_payment_setting.company ,
    }
    list_of_payment_entry = frappe.db.get_all("Payment Entry" , conditions , pluck="name")
    for payment_entry in list_of_payment_entry :

        payment_entry_doc = frappe.get_doc("Payment Entry" , payment_entry)
        make_pay_cheque_gl(payment_entry_doc , optima_payment_setting.default_mode_of_payment , payment_entry_doc.reference_date)
        

def auto_deposit_under_collection_in_time(optima_payment_setting) :
    
    if not optima_payment_setting.enable_auto_deposit_under_collection_in_time : return

    conditions = {
        "payment_type"  :"Receive" ,
        "docstatus" : 1 ,
        "cheque_status" : "For Collection" ,
        "reference_date" : today(),
        "company" : optima_payment_setting.company ,
    }

    list_of_payment_entry = frappe.db.get_all("Payment Entry" , conditions , pluck="name")
    for payment_entry in list_of_payment_entry :

        payment_entry_doc = frappe.get_doc("Payment Entry" , payment_entry)
        make_deposit_under_collection_gl(payment_entry_doc ,payment_entry_doc.reference_date)

    