# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Customer and Supplier statement of account: one party's vouchers over a period, with its opening,
running and closing balance.

The rows come from the site's General Ledger report filtered to the party, as in Process Statement
of Accounts. That is whichever copy the Report record points at: ERPNext's, or one an app swaps in
(wts and property_management ship their own). So the statement's rows, and its Opening and Closing
rows, always equal the General Ledger the users see. The report, the preview page, the PDF, the
email attachment and the Excel file are all built from the same Statement.

A positive balance is a debit (DR). Branching lives in the functions under DECISIONS, which take plain
rows and return values.
"""

import re
from dataclasses import dataclass
from datetime import date

import frappe
from frappe import _
from frappe.core.doctype.report.report import get_report_module_dotted_path
from frappe.utils import flt, fmt_money, formatdate, getdate
from frappe.utils.jinja_globals import is_rtl
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_style

CUSTOMER = "Customer"
SUPPLIER = "Supplier"
REPORTS = {CUSTOMER: "Customer Statement", SUPPLIER: "Supplier Statement"}
GENERAL_LEDGER = "General Ledger"

DR = "DR"
CR = "CR"

# The side a party's balance normally sits on: a customer owes the company, the company owes a
# supplier. The report colours that side green and the other one, an advance or an overpayment, red.
NORMAL_SIDES = {CUSTOMER: DR, SUPPLIER: CR}

# "Balance" and the debit and credit totals already carry translations from other apps that read
# wrong on a statement, so the statement's own wording is looked up under this context.
TRANSLATION_CONTEXT = "Party Statement"

TEMPLATE = "optima_payment/templates/party_statement/statement.html"
STYLESHEET = ("templates", "party_statement", "statement.css")

UNSAFE_FILE_CHARACTERS = re.compile(r'[\\/:*?"<>|]+')


@dataclass(frozen=True)
class Statement:
    opening: float
    entries: list
    total_debit: float
    total_credit: float
    closing: float
    opening_debit: float
    opening_credit: float
    closing_debit: float
    closing_credit: float


@dataclass(frozen=True)
class StatementHeader:
    """Whose statement it is and for which period, as its header shows them."""

    company: str
    company_name_in_arabic: str | None
    party_type: str
    party: str
    party_name: str
    from_date: date
    to_date: date
    currency: str


# ====================================================================================================
# DECISIONS
# Pure: no database.


def validate_party_type(party_type: str) -> None:
    if party_type not in REPORTS:
        frappe.throw(
            _("A statement of account is for a Customer or a Supplier, not {0}.").format(frappe.bold(party_type))
        )


def validate_filters(party_type: str, party, company, from_date, to_date) -> None:
    missing = [
        label
        for label, value in ((party_type, party), ("Company", company), ("From Date", from_date), ("To Date", to_date))
        if not value
    ]
    if missing:
        frappe.throw(
            _("Set {0} first.").format(", ".join(frappe.bold(_(label)) for label in missing)), frappe.MandatoryError
        )

    if getdate(from_date) > getdate(to_date):
        frappe.throw(_("From Date must be on or before To Date."))


def gl_filters(party_type: str, party: str, company: str, from_date, to_date) -> frappe._dict:
    """The General Ledger filters for one party: an opening row, then one row per voucher.

    The voucher grouping is given under both names: ERPNext reads categorize_by, while the older
    copies apps swap in read group_by. exclude_credit_debit_notes is the wts copy's screen default;
    without it the Opening row would differ from the one users see. Other copies ignore the key.
    presentation_currency stays unset, so the ledger reports in the party's account currency.
    """
    return frappe._dict(
        company=company,
        from_date=getdate(from_date),
        to_date=getdate(to_date),
        party_type=party_type,
        party=[party],
        categorize_by="Categorize by Voucher (Consolidated)",
        group_by="Group by Voucher (Consolidated)",
        include_default_book_entries=1,
        show_opening_entries=0,
        exclude_credit_debit_notes=1,
    )


def build_statement(gl_rows: list, precision: int = 2) -> Statement:
    """The statement in ``gl_rows``, the General Ledger's rows for one party.

    The opening is the ledger's leading row, the one without a posting date, debit and credit as the
    ledger shows them: ERPNext's nets them to one side, the copies apps swap in keep both. Every row
    with a voucher is an entry. The ledger's trailing Total and Closing rows are left out: the totals
    and the running balance are recomputed from the entries, rounded at each step so float noise
    never reads as CR, and the Closing row is the opening plus the totals, as every copy builds it.
    """
    opening_debit = opening_credit = 0.0
    if gl_rows and not gl_rows[0].get("posting_date"):
        opening_debit = _round(gl_rows[0].get("debit"), precision)
        opening_credit = _round(gl_rows[0].get("credit"), precision)
    opening = _round(opening_debit - opening_credit, precision)

    balance = opening
    entries = []
    for row in gl_rows:
        if not row.get("voucher_no"):
            continue
        debit, credit = _round(row.get("debit"), precision), _round(row.get("credit"), precision)
        balance = _round(balance + debit - credit, precision)
        entries.append(
            frappe._dict(
                posting_date=row.get("posting_date"),
                voucher_type=row.get("voucher_type"),
                voucher_no=row.get("voucher_no"),
                debit=debit,
                credit=credit,
                balance=balance,
            )
        )

    total_debit = _round(sum(entry.debit for entry in entries), precision)
    total_credit = _round(sum(entry.credit for entry in entries), precision)
    return Statement(
        opening=opening,
        entries=entries,
        total_debit=total_debit,
        total_credit=total_credit,
        closing=_round(opening + total_debit - total_credit, precision),
        opening_debit=opening_debit,
        opening_credit=opening_credit,
        closing_debit=_round(opening_debit + total_debit, precision),
        closing_credit=_round(opening_credit + total_credit, precision),
    )


def _round(value, precision: int) -> float:
    # Float noise such as -2e-13 rounds to -0.0, which would print as "-0" in an export.
    return flt(value, precision) or 0.0


def ledger_currency(filters: dict, company_currency: str) -> str:
    """The currency the ledger reported in. ERPNext's copy records it as presentation_currency; the
    older copies record only an account currency that differs from the company's."""
    return filters.get("presentation_currency") or filters.get("account_currency") or company_currency


def dr_cr(amount: float) -> tuple[float, str | None]:
    """A balance as an unsigned amount and its side. A settled balance has no side."""
    if not amount:
        return 0.0, None
    return abs(amount), CR if amount < 0 else DR


def statement_label(text: str) -> str:
    """``text`` in the statement's own wording (see TRANSLATION_CONTEXT)."""
    return _(text, context=TRANSLATION_CONTEXT)


def balance_text(amount: float, currency: str | None = None) -> str:
    """A balance as the statement writes it: "300.00 DR", "50.00 CR", or "0.00" when settled."""
    unsigned, side = dr_cr(amount)
    money = fmt_money(unsigned, currency=currency)
    return f"{money} {statement_label(side)}" if side else money


def balance_indicator(party_type: str, amount: float) -> str:
    """The report's colour for a balance: Green on the party's normal side, Red on the other, Blue when
    settled. The printed statement goes to the party and is not coloured."""
    _unsigned, side = dr_cr(amount)
    if not side:
        return "Blue"
    return "Green" if side == NORMAL_SIDES[party_type] else "Red"


def band(header: StatementHeader) -> list[str]:
    """The Excel sheet's line above the columns: the party, the period and the currency.

    The print template lays the same line out itself, to keep each date left to right inside
    Arabic text.
    """
    return [
        f"{_(header.party_type)}: {header.party_name}",
        "{0}: {1} {2} {3}".format(
            _("Statement Period"), formatdate(header.from_date), _("to"), formatdate(header.to_date)
        ),
        f"{_('Currency')}: {header.currency}",
    ]


def report_columns() -> list[dict]:
    return [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "voucher_type", "label": _("Voucher Type"), "fieldtype": "Data", "width": 180},
        {
            "fieldname": "voucher_no",
            "label": _("Voucher No."),
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
        {"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "options": "currency", "width": 140},
        {"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "options": "currency", "width": 140},
        {
            "fieldname": "balance",
            "label": statement_label("Balance"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 160,
        },
    ]


def report_rows(statement: Statement, header: StatementHeader) -> list[dict]:
    """The entries between bold Opening Balance and Closing Balance rows, which carry the General
    Ledger's own Opening and Closing debit and credit.

    The balance stays signed, so the report's own export keeps its side; the report's formatter shows
    it as DR or CR, in the colour of the row's indicator.
    """

    def report_row(**fields) -> dict:
        return {
            **fields,
            "currency": header.currency,
            "indicator": balance_indicator(header.party_type, fields["balance"]),
        }

    def label_row(label: str, debit: float, credit: float, balance: float) -> dict:
        return report_row(voucher_type=label, debit=debit, credit=credit, balance=balance, bold=1)

    return [
        label_row(_("Opening Balance"), statement.opening_debit, statement.opening_credit, statement.opening),
        *(report_row(**entry) for entry in statement.entries),
        label_row(_("Closing Balance"), statement.closing_debit, statement.closing_credit, statement.closing),
    ]


def report_summary(statement: Statement, header: StatementHeader) -> list[dict]:
    """The Closing Balance row as cards, so they add up: closing debit − closing credit = balance."""

    def amount_card(label: str, value: float) -> dict:
        return {"label": label, "value": value, "datatype": "Currency", "currency": header.currency}

    return [
        amount_card(_("Closing Debit"), statement.closing_debit),
        amount_card(_("Closing Credit"), statement.closing_credit),
        {
            "label": _("Closing Balance"),
            "value": balance_text(statement.closing, header.currency),
            "datatype": "Data",
            "indicator": balance_indicator(header.party_type, statement.closing),
        },
    ]


def report_message(statement: Statement, header: StatementHeader) -> str:
    """The plain line Frappe shows with the report's cards: what moved in the period alone.

    Its net leaves out the opening, so it is not the closing balance; it is a movement, so it takes no
    colour. Frappe inserts the line as HTML, and dir="ltr" keeps each date's order inside Arabic text.
    """
    return _("For the period {0} to {1}: total debit: {2}, total credit: {3}, net: {4}.").format(
        f'<span dir="ltr">{formatdate(header.from_date)}</span>',
        f'<span dir="ltr">{formatdate(header.to_date)}</span>',
        fmt_money(statement.total_debit, currency=header.currency),
        fmt_money(statement.total_credit, currency=header.currency),
        balance_text(statement.total_debit - statement.total_credit, header.currency),
    )


def excel_rows(statement: Statement, header: StatementHeader) -> list[list]:
    """The preview's Excel sheet, laid out like the PDF. Each balance is unsigned, with its side in the
    column after it."""

    def balance_cells(balance: float) -> list:
        amount, side = dr_cr(balance)
        return [amount, statement_label(side) if side else None]

    return [
        [header.company],
        [_("Statement of Account")],
        [" | ".join(band(header))],
        [],
        [
            _("Date"),
            _("Voucher Type"),
            _("Voucher No."),
            _("Debit"),
            _("Credit"),
            statement_label("Balance"),
            statement_label("DR / CR"),
        ],
        [
            None,
            _("Opening Balance"),
            None,
            statement.opening_debit,
            statement.opening_credit,
            *balance_cells(statement.opening),
        ],
        *(
            [entry.posting_date, _(entry.voucher_type), entry.voucher_no, entry.debit, entry.credit]
            + balance_cells(entry.balance)
            for entry in statement.entries
        ),
        [
            None,
            _("Closing Balance"),
            None,
            statement.closing_debit,
            statement.closing_credit,
            *balance_cells(statement.closing),
        ],
        [],
        [statement_label("Total Debit"), statement.total_debit],
        [statement_label("Total Credit"), statement.total_credit],
        [_("Outstanding Balance"), *balance_cells(statement.closing)],
    ]


def file_name(party: str, to_date, extension: str) -> str:
    """Statement-<party>-<to date>.<extension>, with what a file name can't hold replaced by a dash."""
    return f"Statement-{UNSAFE_FILE_CHARACTERS.sub('-', party)}-{getdate(to_date).isoformat()}.{extension}"


# ====================================================================================================
# LEDGER


def get_statement(party_type: str, party: str, company: str, from_date, to_date) -> tuple[Statement, StatementHeader]:
    """The party's statement from the General Ledger, which applies the user's GL Entry permissions."""
    validate_filters(party_type, party, company, from_date, to_date)

    filters = gl_filters(party_type, party, company, from_date, to_date)
    _columns, rows = general_ledger(filters)

    header = StatementHeader(
        company=company,
        company_name_in_arabic=frappe.get_cached_value("Company", company, "company_name_in_arabic"),
        party_type=party_type,
        party=party,
        party_name=frappe.db.get_value(party_type, party, f"{frappe.scrub(party_type)}_name") or party,
        from_date=getdate(from_date),
        to_date=getdate(to_date),
        currency=ledger_currency(filters, frappe.get_cached_value("Company", company, "default_currency")),
    )
    return build_statement(rows, frappe.get_precision("GL Entry", "debit") or 2), header


def general_ledger(filters: frappe._dict) -> tuple[list, list]:
    """Runs the site's General Ledger report: the copy its Report record points at.

    Report.execute_module would pass the report a copy of ``filters``; the ledger records the currency
    it reported in on the filters it is given, so the module's execute is called directly.
    """
    report = frappe.get_cached_doc("Report", GENERAL_LEDGER)
    execute = frappe.get_attr(f"{get_report_module_dotted_path(report.module, report.name)}.execute")
    columns, rows = execute(filters)[:2]
    return columns, rows


# ====================================================================================================
# RENDERING


def render_html(statement: Statement, header: StatementHeader) -> str:
    """The statement as a standalone print page, for the preview's iframe, the PDF and the attachment."""
    body = frappe.render_template(
        TEMPLATE,
        {
            "statement": statement,
            "header": header,
            "balance_text": balance_text,
            "label": statement_label,
        },
    )
    stylesheet = frappe.read_file(frappe.get_app_path("optima_payment", *STYLESHEET))
    return frappe.render_template(
        "frappe/www/printview.html",
        {
            "body": body,
            "print_style": f"{get_print_style()}\n{stylesheet}",
            "title": f"{_('Statement of Account')} - {header.party_name}",
            "lang": frappe.local.lang,
            "layout_direction": "rtl" if is_rtl() else "ltr",
        },
    )


def render_pdf(statement: Statement, header: StatementHeader) -> bytes:
    return get_pdf(render_html(statement, header))
