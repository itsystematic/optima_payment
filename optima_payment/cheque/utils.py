
from typing import Optional

import frappe
from frappe.utils import cint, flt, getdate
from frappe.utils.data import get_number_format_info

from erpnext import get_company_currency
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.general_ledger import make_gl_entries

from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import add_cheque_action_log


# ================================================================================================
# GENERAL LEDGER ENTRY CREATION
# ================================================================================================
# NOTE: This section could be further improved by extracting all GL-related utilities
# into a dedicated module (e.g., cheque/gl_utils.py) for better cohesion and reusability.

def create_gl_entry(
    doc,
    posting_date,
    account,
    debit=0.0,
    debit_in_account_currency=None,
    credit=0.0,
    credit_in_account_currency=None,
    against=None, party=None,
    party_type=None, remarks=None,
    against_voucher=None,
    against_voucher_type=None,
    cost_center=None,
    exchange_side=None,
):
    """Build cheque GL entry with account-currency amounts derived from base values if not explicitly provided."""
    gl_entry = doc.get_gl_dict({
        "posting_date": posting_date or getdate(),
        "account": account,
        "debit": debit,
        "credit": credit,
        "against": against,
        "party": party,
        "party_type": party_type,
        "remarks": remarks,
        "cost_center": cost_center if cost_center else doc.cost_center,
        "project": doc.project,
        "against_voucher": against_voucher,
        "against_voucher_type": against_voucher_type
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


# ================================================================================================
# GL ENTRY FINALIZATION AND REVERSAL
# ================================================================================================

def finalize_gl_entries(doc, gl_entries, cheque_status=None, mode_of_payment=None, bank_fess_amount=0.00, reverse=False, posting_date=None, cost_center=None):
    """Submit GL entries and log cheque action. Cancels entries if doc is cancelled, unless reverse=True."""
    make_gl_entries(gl_entries, adv_adj=0, merge_entries=False, cancel=0 if doc.get("docstatus") == 1 or reverse == True else 1)
    add_cheque_action_log(
        doc,
        cheque_status,
        mode_of_payment,
        bank_fess_amount,
        posting_date,
        cost_center
    )


def create_party_gl(doc, posting_date=None, remarks=None, gl_entries=None):
    """Generate reversed party GL entries and append to gl_entries list."""
    if gl_entries is None:
        gl_entries = []
    party_gl_entries = []
    doc.add_party_gl_entries(party_gl_entries)
    reverse_gl_manually(party_gl_entries, posting_date, remarks, gl_entries)


def create_advance_gl(doc, posting_date=None, remarks=None, gl_entries=None):
    """Generate reversed advance GL entries and append to gl_entries list."""
    if gl_entries is None:
        gl_entries = []
    advance_gl_entries = []
    doc.add_advance_gl_entries(advance_gl_entries, None)
    reverse_gl_manually(advance_gl_entries, posting_date, remarks, gl_entries)

def reverse_gl_manually(gl_entries_for_action: list[dict], posting_date, remarks, gl_entries):
    """Reverse GL entries by swapping debit/credit and append to target list."""
    for gl_entry in gl_entries_for_action:
        gl_entry.update({
            "posting_date": posting_date if posting_date else getdate(),
            "debit": gl_entry.credit,
            "debit_in_account_currency": gl_entry.credit_in_account_currency,
            "credit": gl_entry.debit,
            "credit_in_account_currency": gl_entry.debit_in_account_currency,
            "remarks": remarks if remarks else "Return Invoice By Cheque {0}".format(gl_entry.voucher_name),
        })
        gl_entries.append(gl_entry)


# ================================================================================================
# NUMBER FORMATTING UTILITIES
# ================================================================================================

@frappe.whitelist()
def money_to_words(
    number,
    main_currency: Optional[str] = None,
    fraction_currency: Optional[str] = None,
) -> str:
    """Spell out an amount as words (e.g. 12.50 -> "Twelve  SAR and  Fifty  Halala.").

    Mirrors Frappe's ``money_in_words`` but keeps this app's cheque-specific
    spacing/formatting. Currency and fraction default to the site's configured
    currency; negative or non-numeric input returns an empty string.
    """
    from frappe.utils import get_defaults

    _ = frappe._

    try:
        number = float(number)
    except ValueError:
        return ""

    number = flt(number)
    if number < 0:
        return ""

    d = get_defaults()
    if not main_currency:
        main_currency = _(d.get("currency", "INR"))
    if not fraction_currency:
        fraction_currency = (
            frappe.db.get_value("Currency", main_currency, "fraction", cache=True)
            or _("Halala")
        )

    number_format = (
        frappe.db.get_value("Currency", main_currency, "number_format", cache=True)
        or frappe.db.get_default("number_format")
        or "#,###.##"
    )

    fraction_length = get_number_format_info(number_format)[2]

    n = "%.{0}f".format(fraction_length) % number

    numbers = n.split(".")
    main, fraction = numbers if len(numbers) > 1 else [n, "00"]

    # Right-pad the fraction so it matches the currency's expected precision.
    if len(fraction) < fraction_length:
        fraction += "0" * (fraction_length - len(fraction))

    # Indian formatting groups by lakh/crore rather than millions.
    in_million = number_format != "#,##,###.##"

    if main == "0" and fraction in ["00", "000"]:
        out = "{0} {1}".format(main_currency, _("Zero"))
    elif main == "0":
        out = _(in_words(fraction, in_million).title()) + "  " + fraction_currency
    else:
        out = _(in_words(main, in_million).title()) + "  " + main_currency
        if cint(fraction):
            out = (
                out
                + " "
                + _("and")
                + "  "
                + _(in_words(fraction, in_million).title())
                + "  "
                + fraction_currency
            )

    return "  " + out + "."



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


