

import frappe 

def journal_entry_on_cancel(doc ,evnet) :

    list_of_accounts = list(filter(lambda x : x.get("reference_type") == "Payment Entry", doc.accounts))

    if not list_of_accounts : return 

    handle_cheque_status_if_exists(list_of_accounts)


def handle_cheque_status_if_exists(list_of_accounts:list=[]) -> None:
    for reference in list_of_accounts :
        payment_entry_doc = frappe.get_doc("Payment Entry" , reference.get("reference_name") )
        
        if payment_entry_doc.get("cheque_status") == "Return To Holder" :
            payment_entry_doc.db_set("cheque_status" , "Rejected")

