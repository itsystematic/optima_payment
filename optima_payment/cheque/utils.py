import frappe
from frappe.utils import getdate
from erpnext.accounts.general_ledger import make_gl_entries
from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import add_cheque_action_log





def create_gl_entry(
    doc, 
    posting_date,
    account, debit=0.0, 
    credit=0.0, 
    against=None, party=None, 
    party_type=None , remarks=None,
    against_voucher =None, 
    against_voucher_type= None 
):
    """Helper to create GL entry dict."""
    return doc.get_gl_dict({
        "posting_date": posting_date or getdate(),
        "account": account,
        "debit": debit,
        "credit": credit,
        "debit_in_account_currency": debit,
        "credit_in_account_currency": credit,
        "against": against,
        "party": party,
        "party_type": party_type,
        "remarks": remarks,
        "cost_center" : doc.cost_center ,
        "project" : doc.project ,
        "against_voucher" : against_voucher,
        "against_voucher_type":against_voucher_type
    }, item=doc)


def finalize_gl_entries(doc , gl_entries, cheque_status=None , mode_of_payment=None , bank_fess_amount=0.00 ,reverse=False, posting_date=None):
    """Finalize GL entries based on the document status and add cheque action log."""
    make_gl_entries(gl_entries, adv_adj=0, merge_entries=False, cancel=0 if doc.get("docstatus") == 1 or reverse ==True else 1)
    add_cheque_action_log(doc , cheque_status , mode_of_payment , bank_fess_amount, posting_date)


def create_jv_for_return_to_holder(doc , posting_date , remarks) :

    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.posting_date = posting_date
    journal_entry.company = doc.company

    journal_entry.append("accounts", {
        "account": doc.get("paid_to"),
        "credit_in_account_currency": doc.paid_amount,
        "credit": doc.paid_amount,
        "cost_center": doc.cost_center ,
        "user_remark" : remarks ,
        
    })

    journal_entry.append("accounts", {
        "account": doc.get("paid_from"),
        "party" : doc.party,
        "party_type" : doc.party_type , 
        "debit_in_account_currency": doc.paid_amount,
        "debit": doc.paid_amount,
        "cost_center": doc.cost_center ,
        "reference_name" : doc.name ,
        "reference_type" : doc.doctype ,
        "against" : doc.get("paid_to") ,
        "user_remark" : remarks
    })
    journal_entry.remarks = remarks
    journal_entry.submit()



def create_party_gl(doc , posting_date=None , remarks=None , gl_entries=[]) :
    party_gl_entries = []
    doc.add_party_gl_entries(party_gl_entries)
    reverse_party_gl(party_gl_entries , posting_date , remarks , gl_entries)


def reverse_party_gl(party_gl_entries:list[dict] , posting_date , remarks , gl_entries) :
    for gl_entry in party_gl_entries :
        gl_entry.update({
            "posting_date" : posting_date if posting_date else getdate(),
            "debit": gl_entry.credit,
            "debit_in_account_currency" : gl_entry.credit_in_account_currency ,
            "credit": gl_entry.debit,
            "credit_in_account_currency" : gl_entry.debit_in_account_currency,
            "remarks" : remarks if remarks else "Return Invoice By Cheque {0}".format(gl_entry.voucher_name),
        })
        gl_entries.append(gl_entry)
