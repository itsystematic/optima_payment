import frappe
from frappe.utils import getdate
from erpnext.accounts.general_ledger import make_gl_entries
from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import add_cheque_action_log

# Main Function

def create_gl_entry(
    doc, 
    posting_date,
    account, debit=0.0, 
    credit=0.0, 
    against=None, party=None, 
    party_type=None , remarks=None,
    against_voucher =None, 
    against_voucher_type= None ,
    cost_center = None
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
        "cost_center" : cost_center if cost_center else doc.cost_center ,
        "project" : doc.project ,
        "against_voucher" : against_voucher,
        "against_voucher_type":against_voucher_type
    }, item=doc)


def finalize_gl_entries(doc , gl_entries, cheque_status=None , mode_of_payment=None , bank_fess_amount=0.00 ,reverse=False, posting_date=None,cost_center=None ) :
    """Finalize GL entries based on the document status and add cheque action log."""
    make_gl_entries(gl_entries, adv_adj=0, merge_entries=False, cancel=0 if doc.get("docstatus") == 1 or reverse ==True else 1)
    add_cheque_action_log(
        doc , 
        cheque_status , 
        mode_of_payment , 
        bank_fess_amount, 
        posting_date, 
        cost_center
    )



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
            "cost_center": gl_entry.cost_center,
            "remarks" : remarks if remarks else "Return Invoice By Cheque {0}".format(gl_entry.voucher_name),
        })
        gl_entries.append(gl_entry)

# Fix Money in Words OF Frappe 
def money_to_words(
    number: str | float | int,
    main_currency: str | None = None,
    fraction_currency: str | None = None,
):
    """
    Returns string in words with currency and fraction currency.
    """
    from frappe.utils import get_defaults , flt , get_number_format_info , cint

    _ = frappe._
    

    try:
        # note: `flt` returns 0 for invalid input and we don't want that
        number = float(number)
    except ValueError:
        return ""

    number = flt(number)
    if number < 0:
        return ""

    d = get_defaults()
    if not main_currency:
        main_currency = d.get("currency", "INR")
    if not fraction_currency:
        fraction_currency = frappe.db.get_value("Currency", main_currency, "fraction", cache=True) or _(
            "Cent"
        )

    number_format = (
        frappe.db.get_value("Currency", main_currency, "number_format", cache=True)
        or frappe.db.get_default("number_format")
        or "#,###.##"
    )

    fraction_length = get_number_format_info(number_format)[2]

    n = f"%.{fraction_length}f" % number

    numbers = n.split(".")
    main, fraction = numbers if len(numbers) > 1 else [n, "00"]

    if len(fraction) < fraction_length:
        zeros = "0" * (fraction_length - len(fraction))
        fraction += zeros

    in_million = True
    if number_format == "#,##,###.##":
        in_million = False

    # 0.00
    if main == "0" and fraction in ["00", "000"]:
        out = _(main_currency, context="Currency") + " " + _("Zero")
    # 0.XX
    elif main == "0":
        out = _(in_words(fraction, in_million).title()) + "  " + _(fraction_currency)
    else:
        out =  _(in_words(main, in_million).title())  + "  "  + _(main_currency)
        if cint(fraction):
            out = (
                out
                + " "
                + _("and")
                + "  "
                + _(in_words(_(fraction), in_million).title())
                + "  "
                + _(fraction_currency)
            )

    return  "  " + out + "  "  + _("only") + " " + "."



def in_words(integer: int, in_million=True) -> str:
    """
    Returns string in words for the given integer.
    """
    from num2words import num2words

    locale = "en_IN" if not in_million else frappe.local.lang
    integer = int(integer)
    try:
        ret = num2words(integer, lang=locale , ordinal=True)
    except NotImplementedError:
        ret = num2words(integer, lang="en" , ordinal=True)
    except OverflowError:
        ret = num2words(integer, lang="en" , ordinal=True)
    return ret.replace("-", " ")


from erpnext.controllers.accounts_controller import get_common_query

def optima_get_advance_payment_entries(
	party_type,
	party,
	party_account,
	order_doctype,
	order_list=None,
	include_unallocated=True,
	against_all_orders=False,
	limit=None,
	condition=None,
):
	payment_entries = []
	payment_entry = frappe.qb.DocType("Payment Entry")

	if order_list or against_all_orders:
		q = get_common_query(
			party_type,
			party,
			party_account,
			limit,
			condition,
		)
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = q.inner_join(payment_ref).on(payment_entry.name == payment_ref.parent)
		q = q.select(
			(payment_ref.allocated_amount).as_("amount"),
			(payment_ref.name).as_("reference_row"),
			(payment_ref.reference_name).as_("against_order"),
		)

		q = q.where(payment_ref.reference_doctype == order_doctype)
		if order_list:
			q = q.where(payment_ref.reference_name.isin(order_list))

		allocated = list(q.run(as_dict=True))
		payment_entries += allocated
	if include_unallocated:
		q = get_common_query(
			party_type,
			party,
			party_account,
			limit,
			condition,
		)
		q = q.select((payment_entry.unallocated_amount).as_("amount"))
		q = q.where(payment_entry.unallocated_amount > 0)
		q = q.where(~payment_entry.cheque_status.isin(['Returned' , 'Rejected' , 'Return To Holder']))

		unallocated = list(q.run(as_dict=True))
		payment_entries += unallocated
    
	return payment_entries
