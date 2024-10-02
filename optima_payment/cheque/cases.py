import frappe
from frappe import _
from optima_payment import active_for_company
from optima_payment.cheque.utils import create_gl_entry , finalize_gl_entries , create_party_gl
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
def make_collect_cheque_gl(doc, mode_of_payment, bank_fees_amount=0.0, posting_date=None):
    default_account = frappe.db.get_value("Optima Payment Setting" , doc.company , "incoming_cheque_wallet_account")
    mode_of_payment_account = get_bank_cash_account(mode_of_payment, doc.get("company")).get("account")
    bank_fees_amount = float(bank_fees_amount) 

    gl_entries = [
        create_gl_entry(doc, posting_date, mode_of_payment_account, debit=doc.get("paid_amount"), against=doc.get("party")),
        create_gl_entry(doc, posting_date, default_account, credit=doc.get("paid_amount"), against=doc.get("party"))
    ]

    if bank_fees_amount:
        bank_fees_expense_account = frappe.db.get_value("Optima Payment Setting", doc.get("company"), "bank_fees_expense_account")
        gl_entries.append(create_gl_entry(doc, posting_date, bank_fees_expense_account, debit=bank_fees_amount, against=doc.party))
        gl_entries.append(create_gl_entry(doc, posting_date, mode_of_payment_account, credit=bank_fees_amount, against=doc.party))

    finalize_gl_entries(doc, gl_entries ,"Collected" , mode_of_payment , bank_fees_amount, posting_date=posting_date)


@active_for_company
def make_cheque_slip_gl(doc , reverse=False ):
    cheque_status = "To Collection"  if reverse else  "Deposited"
    incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")

    gl_entries = [
        create_gl_entry(doc, None, incoming_cheque_wallet_account, debit=doc.paid_amount),
        create_gl_entry(doc, None, doc.paid_to, credit=doc.paid_amount)
    ]

    finalize_gl_entries(doc, gl_entries , cheque_status , reverse=reverse)


@active_for_company
def make_reject_cheque_gl(doc, mode_of_payment, bank_fees_amount=0.0, posting_date=None , remarks=None):

    incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    gl_entries = [
        create_gl_entry(doc, posting_date, incoming_cheque_wallet_account, credit=doc.paid_amount, against=doc.party , remarks=remarks),
        create_gl_entry(doc, posting_date, doc.get("paid_to"), debit=doc.paid_amount, against=doc.party , remarks=remarks)
    ]

    if bank_fees_amount:
        bank_fees_expense_account = frappe.db.get_value("Optima Payment Setting", doc.get("company"), "bank_fees_expense_account")
        mode_of_payment_account = get_bank_cash_account(mode_of_payment, doc.get("company")).get("account")
        gl_entries.append(create_gl_entry(doc, posting_date, bank_fees_expense_account, debit=bank_fees_amount, against=doc.party ,remarks=remarks))
        gl_entries.append(create_gl_entry(doc, posting_date, mode_of_payment_account, credit=bank_fees_amount, against=doc.party, remarks=remarks))

    finalize_gl_entries(doc, gl_entries , "Rejected" , mode_of_payment , bank_fees_amount, posting_date=posting_date)


@active_for_company
def make_return_cheque_gl(doc , posting_date=None , remarks=None) :

    incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")
    gl_entries = [
        create_gl_entry(doc, posting_date, doc.get("paid_to"), debit=doc.paid_amount, against=doc.party ,remarks=remarks) ,
        create_gl_entry(doc, posting_date, incoming_cheque_wallet_account, credit=doc.paid_amount, against=doc.party , remarks=remarks) ,
        create_gl_entry(doc, posting_date, doc.get("paid_to"), credit=doc.paid_amount, against=doc.party ,remarks=remarks) ,
    ]
    create_party_gl(doc , posting_date , remarks , gl_entries)
    finalize_gl_entries(doc, gl_entries , "Returned", posting_date=posting_date )


@active_for_company
def make_endorsed_cheque_gl(doc, against_payment_entry, posting_date=None):
    gl_entries = [
        create_gl_entry(doc, posting_date, against_payment_entry.get("paid_to"),credit=doc.paid_amount, against_voucher_type= "Payment Entry" , against_voucher= doc.receivable_cheque  ),
        create_gl_entry(doc, posting_date, doc.paid_to, debit=doc.paid_amount, against=against_payment_entry.get("paid_to"),party=doc.party, party_type=doc.party_type,)
    ]

    finalize_gl_entries(doc, gl_entries , "Endorsed", posting_date=posting_date)
    

@active_for_company
def make_deposit_under_collection_gl(doc, posting_date=None):
    incoming_cheque_wallet_account = frappe.db.get_value("Optima Payment Setting", doc.company, "incoming_cheque_wallet_account")

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

    finalize_gl_entries(doc, gl_entries , "Return To Holder", posting_date=posting_date )

