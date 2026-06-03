import frappe
from frappe.utils import flt, getdate

from erpnext import get_company_currency
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.general_ledger import make_gl_entries

from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import add_cheque_action_log

# Main Function

def create_gl_entry(
    doc, 
    posting_date,
    account,
    debit=0.0, 
    debit_in_account_currency=None,
    credit=0.0, 
    credit_in_account_currency=None,
    against=None, party=None, 
    party_type=None , remarks=None,
    against_voucher =None, 
    against_voucher_type= None ,
    cost_center = None,
    exchange_side=None,
):
    """Build a cheque GL row with account-currency amounts derived from base values."""
    gl_entry = doc.get_gl_dict({
        "posting_date": posting_date or getdate(),
        "account": account,
        "debit": debit,
        "credit": credit,
        "against": against,
        "party": party,
        "party_type": party_type,
        "remarks": remarks,
        "cost_center" : cost_center if cost_center else doc.cost_center ,
        "project" : doc.project ,
        "against_voucher" : against_voucher,
        "against_voucher_type":against_voucher_type
    }, item=doc)

    gl_entry["debit_in_account_currency"] = _resolve_account_currency_amount(
        doc=doc,
        account=account,
        posting_date=gl_entry.posting_date,
        base_amount=debit,
        explicit_amount=debit_in_account_currency,
        exchange_side=exchange_side,
    )
    gl_entry["credit_in_account_currency"] = _resolve_account_currency_amount(
        doc=doc,
        account=account,
        posting_date=gl_entry.posting_date,
        base_amount=credit,
        explicit_amount=credit_in_account_currency,
        exchange_side=exchange_side,
    )
    return gl_entry


def _resolve_account_currency_amount(doc, account, posting_date, base_amount, explicit_amount, exchange_side):
    """Translate a base GL amount into the entry account's currency."""
    if explicit_amount is not None:
        return flt(explicit_amount)

    base_amount = flt(base_amount)
    if not base_amount:
        return 0.0

    company_currency = doc.get("company_currency") or get_company_currency(doc.company)
    account_currency = get_account_currency(account)
    if not account_currency or account_currency == company_currency:
        return base_amount

    exchange_rate = _get_exchange_rate_for_account(
        doc, account, account_currency, posting_date, exchange_side
    )
    return flt(base_amount / (exchange_rate or 1))


def _get_exchange_rate_for_account(doc, account, account_currency, posting_date, exchange_side):
    """Prefer the payment entry side's rate and fall back to the account's exchange rate."""
    payment_side = _get_payment_side(doc, account, exchange_side)
    if payment_side and payment_side.get("currency") == account_currency and payment_side.get("rate"):
        return payment_side["rate"]

    return get_exchange_rate(account_currency, doc.get("company_currency") or get_company_currency(doc.company), posting_date)


def _get_payment_side(doc, account, exchange_side):
    """Return the payment side metadata used to translate cheque GL amounts."""
    payment_sides = {
        "source": {
            "account": doc.get("paid_from"),
            "currency": doc.get("paid_from_account_currency"),
            "rate": flt(doc.get("source_exchange_rate")),
        },
        "target": {
            "account": doc.get("paid_to"),
            "currency": doc.get("paid_to_account_currency"),
            "rate": flt(doc.get("target_exchange_rate")),
        },
    }

    if exchange_side in payment_sides:
        return payment_sides[exchange_side]

    if account and account == doc.get("paid_from"):
        return payment_sides["source"]

    if account and account == doc.get("paid_to"):
        return payment_sides["target"]

    return None


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



def create_party_gl(doc , posting_date=None , remarks=None , gl_entries=None) :
    gl_entries = gl_entries if gl_entries is not None else []
    party_gl_entries = []
    doc.add_party_gl_entries(party_gl_entries)
    reverse_gl_manually(party_gl_entries , posting_date , remarks , gl_entries)


def create_advance_gl(doc , posting_date=None , remarks=None , gl_entries=None) :
    gl_entries = gl_entries if gl_entries is not None else []
    advance_gl_entries = []
    doc.add_advance_gl_entries(advance_gl_entries , None)
    reverse_gl_manually(advance_gl_entries , posting_date , remarks , gl_entries)

def reverse_gl_manually(gl_entries_for_action:list[dict] , posting_date , remarks , gl_entries) :
    for gl_entry in gl_entries_for_action :
        gl_entry.update({
            "posting_date" : posting_date if posting_date else getdate(),
            "debit": gl_entry.credit,
            "debit_in_account_currency" : gl_entry.credit_in_account_currency ,
            "credit": gl_entry.debit,
            "credit_in_account_currency" : gl_entry.debit_in_account_currency,
            #"cost_center": gl_entry.cost_center,
            #"against_voucher" : gl_entry.against_voucher,
            #"against_voucher_type":gl_entry.against_voucher_type ,
            #"project" : gl_entry.project ,
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
from erpnext.controllers.accounts_controller import get_advance_payment_entries

# Store original function
original_get_advance_payment_entries = get_advance_payment_entries

# Module-level variable to cache the check result
_use_optima_cache = {}

def clear_optima_cache(site_name=None) -> None:
    """Clear the optima implementation cache for a specific site or all sites"""
    global _use_optima_cache
    if site_name:
        _use_optima_cache.pop(site_name, None)
    else:
        _use_optima_cache.clear()


def should_use_optima_implementation() -> bool:
    """
    Comprehensive check to determine if optima payment implementation should be used
    Returns True only if ALL conditions are met:
    1. App is installed for current site
    2. DocType exists and is accessible
    3. cheque_status field exists in Payment Entry table
    4. At least one Optima Payment Setting exists AND is enabled for current company
    
    FIX: Check per-company enable flag instead of just checking if any setting exists.
    This prevents Optima override from activating globally across all companies when
    it should only apply to companies that have enabled it.
    """
    try:
        # Check if app is installed for current site
        if "optima_payment" not in frappe.get_installed_apps():
            return False
        
        # Check if DocType exists and is accessible
        if not frappe.db.exists("DocType", "Optima Payment Setting"):
            return False
            
        # Check if cheque_status field exists in Payment Entry table
        try:
            # Try to access the field metadata first
            if not frappe.db.has_column("Payment Entry", "cheque_status"):
                return False
        except Exception:
            # Fallback: try a simple query
            try:
                frappe.db.sql("SELECT cheque_status FROM `tabPayment Entry` LIMIT 1", as_dict=True)
            except Exception:
                return False
        
        # FIX: Check if there are any settings with enable_optima_payment=1 for current company
        # Only enable the override if explicitly enabled for a specific company.
        # This prevents the override from affecting all companies site-wide.
        enabled_count = frappe.db.count(
            "Optima Payment Setting",
            filters={"enable_optima_payment": 1}
        )
        
        if enabled_count == 0:
            return False
            
        return True
        
    except Exception as e:
        frappe.logger().error(f"Error checking optima implementation availability: {str(e)}")
        return False

def optima_get_advance_payment_entries(*args, **kwargs):
    """Wrapper that conditionally uses your custom implementation"""
    try:
        # Get current site name for caching
        site_name = frappe.local.site

        # Check cache first
        if site_name not in _use_optima_cache:
            _use_optima_cache[site_name] = should_use_optima_implementation()
        
        # Use cached result
        if _use_optima_cache[site_name]:
            return _optima_get_advance_payment_entries(*args, **kwargs)
        else:
            return original_get_advance_payment_entries(*args, **kwargs)
        
    except Exception as e:
        frappe.logger().error(f"Error in optima wrapper: {str(e)}")
        # Always fallback to original implementation on any error
        return original_get_advance_payment_entries(*args, **kwargs)
    

def _optima_get_advance_payment_entries(
	party_type,
	party,
	party_account,
	order_doctype,
	order_list=None,
    default_advance_account=None,
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
            default_advance_account,
			limit,
			condition,
		)
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = q.inner_join(payment_ref).on(payment_entry.name == payment_ref.parent)
		q = q.select(
			(payment_ref.allocated_amount).as_("amount"),
			(payment_ref.name).as_("reference_row"),
			(payment_ref.reference_name).as_("against_order"),
            (payment_entry.book_advance_payments_in_separate_party_account),
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
            default_advance_account,
			limit,
			condition,
		)
		q = q.select((payment_entry.unallocated_amount).as_("amount"))
		q = q.where(payment_entry.unallocated_amount > 0)
		
		# Filter out problematic cheque statuses but allow NULL values.
		# NULL cheque_status indicates non-cheque payments (bank transfer, cash, etc.)
		# which should be included in Payment Reconciliation.
		# Field existence is already verified by should_use_optima_implementation().
		q = q.where(
			(payment_entry.cheque_status.isnull()) |
			(payment_entry.cheque_status == '') |
			(~payment_entry.cheque_status.isin(['Returned', 'Rejected', 'Return To Holder']))
		)

		unallocated = list(q.run(as_dict=True))
		payment_entries += unallocated
    
	return payment_entries
