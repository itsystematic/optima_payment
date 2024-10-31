# import frappe
from frappe import _
from optima_payment import active_for_company , get_cheque_account
from optima_payment.cheque.utils import ( 
    create_gl_entry , 
    finalize_gl_entries , 
    create_party_gl ,
    create_advance_gl
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account



@active_for_company
def make_pay_cheque_gl(doc, mode_of_payment=None, posting_date=None):
    mode_of_payment_account = get_bank_cash_account(mode_of_payment, doc.get("company")).get("account")

    gl_entries = [
        create_gl_entry(doc, posting_date, doc.get("paid_from"), debit=doc.paid_amount, against=doc.party),
        create_gl_entry(doc, posting_date, mode_of_payment_account, credit=doc.paid_amount, against=doc.party)
    ]

    finalize_gl_entries(doc, gl_entries ,'Encashment' , mode_of_payment, posting_date=posting_date)


@active_for_company
def make_collect_cheque_gl(doc, mode_of_payment, bank_fees_commission=0.0, posting_date=None, cost_center=None):
    # default_account = frappe.db.get_value("Optima Payment Setting" , doc.company , "incoming_cheque_wallet_account")
    default_account = get_cheque_account(doc , "incoming_cheque_wallet_account")
    mode_of_payment_account = get_bank_cash_account(mode_of_payment, doc.get("company")).get("account")
    bank_fees_commission = float(bank_fees_commission) 

    gl_entries = [
        create_gl_entry(doc, posting_date, mode_of_payment_account, debit=doc.get("paid_amount"), against=doc.get("party")),
        create_gl_entry(doc, posting_date, default_account, credit=doc.get("paid_amount"), against=doc.get("party"))
    ]

    if bank_fees_commission:
        # bank_fees_expense_account = frappe.db.get_value("Optima Payment Setting", doc.get("company"), "bank_commission_account")
        bank_fees_expense_account = get_cheque_account(doc , "bank_commission_account")
        gl_entries.append(create_gl_entry(doc, posting_date, bank_fees_expense_account, debit=bank_fees_commission, against=doc.party, cost_center=cost_center))
        gl_entries.append(create_gl_entry(doc, posting_date, mode_of_payment_account, credit=bank_fees_commission, against=doc.party))

    finalize_gl_entries(doc, gl_entries ,"Collected" , mode_of_payment , bank_fees_commission, posting_date=posting_date,cost_center=cost_center)


@active_for_company
def make_cheque_slip_gl(doc , reverse=False ):
    cheque_status = "To Collection"  if reverse else  "Deposited"
    # incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    incoming_cheque_wallet_account = get_cheque_account(doc , "incoming_cheque_wallet_account")

    gl_entries = [
        create_gl_entry(doc, None, incoming_cheque_wallet_account, debit=doc.paid_amount),
        create_gl_entry(doc, None, doc.paid_to, credit=doc.paid_amount)
    ]

    finalize_gl_entries(doc, gl_entries , cheque_status , reverse=reverse)


@active_for_company
def make_reject_cheque_gl(doc, mode_of_payment, bank_fees_amount=0.0, posting_date=None ,cost_center=None, remarks=None ):

    # incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    incoming_cheque_wallet_account = get_cheque_account(doc , "incoming_cheque_wallet_account")
    gl_entries = [
        create_gl_entry(doc, posting_date, incoming_cheque_wallet_account, credit=doc.paid_amount, against=doc.party , remarks=remarks),
        create_gl_entry(doc, posting_date, doc.get("paid_to"), debit=doc.paid_amount, against=doc.party , remarks=remarks)
    ]

    if bank_fees_amount:
        # bank_fees_expense_account = frappe.db.get_value("Optima Payment Setting", doc.get("company"), "bank_fees_expense_account")
        bank_fees_expense_account = get_cheque_account(doc , "bank_fees_expense_account")
        mode_of_payment_account = get_bank_cash_account(mode_of_payment, doc.get("company")).get("account")
        gl_entries.append(create_gl_entry(doc, posting_date, bank_fees_expense_account, debit=bank_fees_amount, against=doc.party ,remarks=remarks, cost_center=cost_center))
        gl_entries.append(create_gl_entry(doc, posting_date, mode_of_payment_account, credit=bank_fees_amount, against=doc.party, remarks=remarks))

    finalize_gl_entries(doc, gl_entries , "Rejected" , mode_of_payment , bank_fees_amount, posting_date=posting_date,cost_center=cost_center)


@active_for_company
def make_return_cheque_gl(doc , posting_date=None , remarks=None) :

    # incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    incoming_cheque_wallet_account = get_cheque_account(doc , "incoming_cheque_wallet_account")
    gl_entries = [
        create_gl_entry(doc, posting_date, doc.get("paid_to"), debit=doc.paid_amount, against=doc.party ,remarks=remarks) ,
        create_gl_entry(doc, posting_date, incoming_cheque_wallet_account, credit=doc.paid_amount, against=doc.party , remarks=remarks) ,
        create_gl_entry(doc, posting_date, doc.get("paid_to"), credit=doc.paid_amount, against=doc.party ,remarks=remarks) ,
    ]
    create_party_gl(doc , posting_date , remarks , gl_entries)
    create_advance_gl(doc, posting_date , remarks , gl_entries)
    finalize_gl_entries(doc, gl_entries , "Returned", posting_date=posting_date )



@active_for_company
def make_deposit_under_collection_gl(doc, posting_date=None):
    # incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    incoming_cheque_wallet_account = get_cheque_account(doc , "incoming_cheque_wallet_account")

    gl_entries = [
        create_gl_entry(doc, posting_date, incoming_cheque_wallet_account, debit=doc.paid_amount, against=doc.party),
        create_gl_entry(doc, posting_date, doc.get("paid_to"), credit=doc.paid_amount, against=doc.party)
    ]

    finalize_gl_entries(doc, gl_entries ,"Deposit Under Collection", posting_date=posting_date)


@active_for_company
def make_return_to_holder_gl(doc , posting_date , remarks=None) :

    gl_entries = [
        create_gl_entry(doc, posting_date, doc.get("paid_to"), credit=doc.paid_amount, against=doc.party ,remarks=remarks) ,
    ]
    create_party_gl(doc , posting_date , remarks , gl_entries)
    create_advance_gl(doc, posting_date , remarks , gl_entries)
    finalize_gl_entries(doc, gl_entries , "Return To Holder", posting_date=posting_date )

