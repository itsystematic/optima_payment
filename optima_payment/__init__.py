__version__ = "15.0.0"


import frappe
from erpnext.controllers import accounts_controller
from optima_payment.cheque.utils import optima_get_advance_payment_entries

def active_for_company(fn) :
    
    def caller(doc , *args , **kwargs) : 
        if not frappe.db.exists("Optima Payment Setting", { "company" : doc.get("company") , "enable_optima_payment" : 1}) : 
            return 
        return fn(doc, *args , **kwargs)
        
    return caller



def get_applicable_campanies_optima_payment(company=None) :

    list_setting_doc = []
    conditions = {"enable_optima_payment" : 1}

    if company : conditions["company"] = company

    list_of_companies = frappe.db.get_all("Optima Payment Setting" , conditions, pluck="name")
    for optima_payment_setting in list_of_companies :
        list_setting_doc.append( frappe.get_doc("Optima Payment Setting" , optima_payment_setting))
    
    return list_setting_doc


# Overwrite get_advance_payment_entries
# TO Skip Cheque Status ( Return , Reject )
accounts_controller.get_advance_payment_entries = optima_get_advance_payment_entries