__version__ = "15.0.0"


"""
    Main File For Optima Payment

    1. Overwrite get_advance_payment_entries
    2. Main Function To GET Account by Currency in Optima Payment Setting
    3. Main Function To GET All Company in Optima Payment Setting ( Enabled )

"""

import frappe
from frappe import _
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


def get_cheque_account(doc:frappe._dict , fieldname:str ) -> str|None :
    """ Main Function To GET Account by Currency in Optima Payment Setting """

    default_currency = doc.paid_to_account_currency if doc.payment_type == "Receive" else doc.paid_from_account_currency
    account = frappe.db.get_value("Cheque Accounts" , {"parent" : doc.company , "default_currency" : default_currency} , fieldname)

    if not account : 
        frappe.throw(_("You Must Define {0} wiht Currency {1} in Optima Payment Setting For This Company {2}").format(
                frappe.bold(fieldname.replace("_" , " ").title()) ,
                frappe.bold(default_currency) ,
                frappe.bold(doc.company)
            )
        )
    return account


# Overwrite get_advance_payment_entries
# TO Skip Cheque Status ( Return , Reject )
accounts_controller.get_advance_payment_entries = optima_get_advance_payment_entries