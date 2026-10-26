# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The branch matrix for the statement of account. Nothing here writes to the database.

Rows are ``frappe._dict`` objects shaped like the General Ledger's, so no party or voucher has to
exist on the site. The wiring through the real ledger is in test_statement_integration.py.
"""

import math
from dataclasses import replace
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import fmt_money, formatdate, getdate

from optima_payment.party_statement.statement import (
    CR,
    DR,
    Statement,
    StatementHeader,
    balance_indicator,
    balance_text,
    band,
    build_statement,
    dr_cr,
    excel_rows,
    file_name,
    gl_filters,
    ledger_currency,
    render_html,
    report_columns,
    report_message,
    report_rows,
    report_summary,
    validate_filters,
    validate_party_type,
)

CUSTOMER = "Al Noor Trading"
COMPANY = "Optima Test Company"
FROM_DATE = "2026-01-01"
TO_DATE = "2026-06-30"
CURRENCY = "SAR"


def opening_row(debit=0.0, credit=0.0):
    return frappe._dict(account="'Opening'", debit=debit, credit=credit)


def entry_row(voucher_no, *, debit=0.0, credit=0.0, voucher_type="Sales Invoice", posting_date="2026-02-01"):
    return frappe._dict(
        posting_date=getdate(posting_date),
        voucher_type=voucher_type,
        voucher_no=voucher_no,
        account="Debtors - OTC",
        debit=debit,
        credit=credit,
    )


def trailing_rows(debit=0.0, credit=0.0):
    """The ledger's Total and Closing rows, which the statement recomputes instead of reading."""
    return [
        frappe._dict(account="'Total'", debit=debit, credit=credit),
        frappe._dict(account="'Closing (Opening + Total)'", debit=debit, credit=credit),
    ]


def make_header(party_type="Customer"):
    return StatementHeader(
        company=COMPANY,
        company_name_in_arabic=None,
        party_type=party_type,
        party=CUSTOMER,
        party_name=CUSTOMER,
        from_date=getdate(FROM_DATE),
        to_date=getdate(TO_DATE),
        currency=CURRENCY,
    )


class TestGlFilters(FrappeTestCase):
    def test_one_party_one_row_per_voucher_after_an_opening_row(self):
        filters = gl_filters("Customer", CUSTOMER, COMPANY, FROM_DATE, TO_DATE)

        self.assertEqual(
            filters,
            {
                "company": COMPANY,
                "from_date": date(2026, 1, 1),
                "to_date": date(2026, 6, 30),
                "party_type": "Customer",
                "party": [CUSTOMER],
                "categorize_by": "Categorize by Voucher (Consolidated)",
                "group_by": "Group by Voucher (Consolidated)",
                "include_default_book_entries": 1,
                "show_opening_entries": 0,
                "exclude_credit_debit_notes": 1,
            },
        )

    def test_the_currency_is_left_to_the_ledger(self):
        self.assertNotIn("presentation_currency", gl_filters("Customer", CUSTOMER, COMPANY, FROM_DATE, TO_DATE))


def empty_statement(opening_debit=0.0, opening_credit=0.0):
    """A statement with no entries: its Closing row repeats its Opening row."""
    opening = opening_debit - opening_credit
    return Statement(
        opening=opening,
        entries=[],
        total_debit=0.0,
        total_credit=0.0,
        closing=opening,
        opening_debit=opening_debit,
        opening_credit=opening_credit,
        closing_debit=opening_debit,
        closing_credit=opening_credit,
    )


class TestBuildStatement(FrappeTestCase):
    def test_an_empty_period_keeps_the_opening_as_the_closing(self):
        statement = build_statement([opening_row(debit=250), *trailing_rows()])

        self.assertEqual(statement, empty_statement(opening_debit=250.0))

    def test_a_party_with_no_ledger_rows_is_all_zero(self):
        cases = [
            ("no rows at all", []),
            ("zero opening and no entries", [opening_row(), *trailing_rows()]),
        ]
        for label, rows in cases:
            with self.subTest(case=label):
                self.assertEqual(build_statement(rows), empty_statement())

    def test_a_credit_opening_is_negative(self):
        self.assertEqual(build_statement([opening_row(credit=80)]).opening, -80.0)

    def test_the_opening_keeps_debit_and_credit_as_the_ledger_shows_them(self):
        cases = [
            ("netted to one side, as in ERPNext", opening_row(debit=60), (60.0, 0.0)),
            (
                "both sides, as in the copies apps swap in",
                opening_row(debit=1700861.32, credit=1700801.32),
                (1700861.32, 1700801.32),
            ),
        ]
        for label, row, sides in cases:
            with self.subTest(case=label):
                statement = build_statement([row])
                self.assertEqual((statement.opening_debit, statement.opening_credit), sides)
                self.assertEqual(statement.opening, 60.0)

    def test_the_closing_row_is_the_opening_plus_the_totals(self):
        statement = build_statement(
            [opening_row(debit=100, credit=40), entry_row("PE-1", credit=30), entry_row("SINV-1", debit=50)]
        )

        self.assertEqual((statement.closing_debit, statement.closing_credit), (150.0, 70.0))
        self.assertEqual(statement.closing, statement.closing_debit - statement.closing_credit)

    def test_without_a_leading_opening_row_the_opening_is_zero(self):
        statement = build_statement([entry_row("SINV-1", debit=100)])

        self.assertEqual(statement.opening, 0.0)
        self.assertEqual(statement.closing, 100.0)

    def test_the_running_balance_crosses_zero(self):
        statement = build_statement(
            [
                opening_row(debit=100),
                entry_row("PE-1", credit=150, voucher_type="Payment Entry"),
                entry_row("SINV-1", debit=80),
                entry_row("PE-2", credit=30, voucher_type="Payment Entry"),
                *trailing_rows(),
            ]
        )

        self.assertEqual([entry.balance for entry in statement.entries], [-50.0, 30.0, 0.0])

    def test_closing_is_opening_plus_debits_minus_credits(self):
        statement = build_statement(
            [opening_row(credit=40), entry_row("SINV-1", debit=500), entry_row("PE-1", credit=120.5)]
        )

        self.assertEqual((statement.total_debit, statement.total_credit), (500.0, 120.5))
        self.assertEqual(statement.closing, -40 + 500 - 120.5)
        self.assertEqual(statement.closing, statement.entries[-1].balance)

    def test_the_ledgers_own_total_and_closing_rows_are_ignored(self):
        statement = build_statement([opening_row(), entry_row("SINV-1", debit=100), *trailing_rows(999, 1)])

        self.assertEqual([entry.voucher_no for entry in statement.entries], ["SINV-1"])
        self.assertEqual(statement.closing, 100.0)

    def test_an_entry_keeps_its_voucher_and_both_sides(self):
        (entry,) = build_statement([entry_row("SINV-1", debit=174, credit=174)]).entries

        self.assertEqual(
            entry,
            {
                "posting_date": date(2026, 2, 1),
                "voucher_type": "Sales Invoice",
                "voucher_no": "SINV-1",
                "debit": 174.0,
                "credit": 174.0,
                "balance": 0.0,
            },
        )

    def test_float_noise_rounds_to_a_positive_zero(self):
        """The ledger has summed an opening of 2.2737e-13 CR on a real site; it must read 0.00."""
        statement = build_statement([opening_row(credit=2.2737367544323206e-13)])

        self.assertEqual(statement.opening, 0.0)
        self.assertEqual(math.copysign(1, statement.opening), 1.0)

    def test_amounts_round_to_the_given_precision(self):
        statement = build_statement([entry_row("SINV-1", debit=10.006)], precision=2)

        self.assertEqual(statement.entries[0].debit, 10.01)


class TestLedgerCurrency(FrappeTestCase):
    def test_the_first_currency_the_ledger_recorded_wins(self):
        cases = [
            ("presentation currency", {"presentation_currency": "USD", "account_currency": "EUR"}, "USD"),
            ("account currency only, as older copies record it", {"account_currency": "EUR"}, "EUR"),
            ("neither", {}, CURRENCY),
        ]
        for label, filters, currency in cases:
            with self.subTest(case=label):
                self.assertEqual(ledger_currency(filters, CURRENCY), currency)


class TestDrCr(FrappeTestCase):
    def test_the_sign_picks_the_side_and_zero_has_none(self):
        cases = [
            ("debit", 24495.0, (24495.0, DR)),
            ("credit", -27324.45, (27324.45, CR)),
            ("zero", 0.0, (0.0, None)),
            ("negative zero", -0.0, (0.0, None)),
        ]
        for label, amount, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(dr_cr(amount), expected)


class TestBalanceText(FrappeTestCase):
    def test_the_amount_and_its_side_or_the_amount_alone_when_settled(self):
        cases = [
            ("debit", 300.0, None, f"{fmt_money(300.0)} DR"),
            ("credit", -50.0, None, f"{fmt_money(50.0)} CR"),
            ("settled", 0.0, None, fmt_money(0.0)),
            ("with a currency", 300.0, CURRENCY, f"{fmt_money(300.0, currency=CURRENCY)} DR"),
        ]
        for label, amount, currency, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(balance_text(amount, currency), expected)


class TestBalanceIndicator(FrappeTestCase):
    def test_green_on_the_partys_normal_side_red_on_the_other_and_blue_when_settled(self):
        cases = [
            ("customer owes the company", "Customer", 100.0, "Green"),
            ("customer paid in advance", "Customer", -100.0, "Red"),
            ("customer settled", "Customer", 0.0, "Blue"),
            ("company owes the supplier", "Supplier", -100.0, "Green"),
            ("supplier overpaid", "Supplier", 100.0, "Red"),
            ("supplier settled", "Supplier", 0.0, "Blue"),
        ]
        for label, party_type, amount, indicator in cases:
            with self.subTest(case=label):
                self.assertEqual(balance_indicator(party_type, amount), indicator)


class TestValidation(FrappeTestCase):
    def test_customer_and_supplier_are_the_only_party_types(self):
        for party_type in ("Customer", "Supplier"):
            with self.subTest(party_type=party_type):
                validate_party_type(party_type)

        with self.assertRaisesRegex(frappe.ValidationError, "for a Customer or a Supplier, not .*Employee"):
            validate_party_type("Employee")

    def test_every_filter_is_required_and_named_when_missing(self):
        cases = [
            ("party", ("Customer", None, COMPANY, FROM_DATE, TO_DATE), "Customer"),
            ("company", ("Customer", CUSTOMER, None, FROM_DATE, TO_DATE), "Company"),
            ("from date", ("Customer", CUSTOMER, COMPANY, None, TO_DATE), "From Date"),
            ("to date", ("Customer", CUSTOMER, COMPANY, FROM_DATE, None), "To Date"),
        ]
        for label, args, named in cases:
            with self.subTest(missing=label):
                with self.assertRaisesRegex(frappe.MandatoryError, named):
                    validate_filters(*args)

    def test_the_period_may_be_one_day_but_not_reversed(self):
        validate_filters("Customer", CUSTOMER, COMPANY, TO_DATE, TO_DATE)

        with self.assertRaisesRegex(frappe.ValidationError, "From Date must be on or before To Date"):
            validate_filters("Customer", CUSTOMER, COMPANY, TO_DATE, FROM_DATE)


class TestReportColumns(FrappeTestCase):
    def test_amount_headers_name_the_currency_over_plain_numbers(self):
        amounts = report_columns(CURRENCY)[3:]

        self.assertEqual(
            [(column["label"], column["fieldtype"]) for column in amounts],
            [(f"Debit ({CURRENCY})", "Float"), (f"Credit ({CURRENCY})", "Float"), (f"Balance ({CURRENCY})", "Float")],
        )
        self.assertFalse(any("options" in column for column in amounts))


class TestReportRows(FrappeTestCase):
    def setUp(self):
        self.statement = build_statement(
            [opening_row(debit=100), entry_row("PE-1", credit=150, voucher_type="Payment Entry")]
        )

    def test_bold_opening_and_closing_rows_carry_the_ledgers_debit_and_credit(self):
        rows = report_rows(self.statement, make_header())

        self.assertEqual(
            rows[0],
            {
                "voucher_type": "Opening Balance",
                "debit": 100.0,
                "credit": 0.0,
                "balance": 100.0,
                "indicator": "Green",
                "bold": 1,
            },
        )
        self.assertEqual(
            rows[-1],
            {
                "voucher_type": "Closing Balance",
                "debit": 100.0,
                "credit": 150.0,
                "balance": -50.0,
                "indicator": "Red",
                "bold": 1,
            },
        )
        self.assertEqual([row["voucher_no"] for row in rows[1:-1]], ["PE-1"])

    def test_entries_keep_a_signed_balance(self):
        entry = report_rows(self.statement, make_header())[1]

        self.assertEqual(entry["balance"], -50.0)
        self.assertNotIn("bold", entry)

    def test_each_row_is_coloured_for_its_party_type(self):
        cases = [("Customer", ["Green", "Red", "Red"]), ("Supplier", ["Red", "Green", "Green"])]
        for party_type, indicators in cases:
            with self.subTest(party_type=party_type):
                rows = report_rows(self.statement, make_header(party_type))
                self.assertEqual([row["indicator"] for row in rows], indicators)


class TestReportSummary(FrappeTestCase):
    def setUp(self):
        # Opening 100 DR, then 300 owed and 120 paid: closing 280 DR.
        self.statement = build_statement(
            [opening_row(debit=100), entry_row("SINV-1", debit=300), entry_row("PE-1", credit=120)]
        )

    def test_the_cards_are_the_closing_balance_row(self):
        closing_debit, closing_credit, closing_balance = report_summary(self.statement, make_header())
        closing_row = report_rows(self.statement, make_header())[-1]

        self.assertEqual(
            (closing_debit["label"], closing_debit["value"], closing_debit["datatype"], closing_debit["currency"]),
            ("Closing Debit", closing_row["debit"], "Currency", CURRENCY),
        )
        self.assertEqual((closing_credit["label"], closing_credit["value"]), ("Closing Credit", closing_row["credit"]))
        self.assertEqual(
            (closing_balance["label"], closing_balance["value"]), ("Closing Balance", balance_text(280.0, CURRENCY))
        )

    def test_the_closing_balance_is_coloured_for_the_party_type(self):
        cases = [
            ("customer owes the company", "Customer", [entry_row("SINV-1", debit=10)], "Green"),
            ("customer settled", "Customer", [], "Blue"),
            ("customer paid in advance", "Customer", [entry_row("PE-1", credit=10)], "Red"),
            ("company owes the supplier", "Supplier", [entry_row("PINV-1", credit=10)], "Green"),
            ("supplier settled", "Supplier", [], "Blue"),
            ("supplier overpaid", "Supplier", [entry_row("PE-1", debit=10)], "Red"),
        ]
        for label, party_type, rows, indicator in cases:
            with self.subTest(case=label):
                closing_balance = report_summary(build_statement(rows), make_header(party_type))[2]
                self.assertEqual(closing_balance["indicator"], indicator)

    def test_a_settled_closing_balance_reads_without_a_side(self):
        closing_balance = report_summary(build_statement([]), make_header())[2]

        self.assertEqual(closing_balance["value"], balance_text(0.0, CURRENCY))
        self.assertFalse(closing_balance["value"].endswith(DR))


class TestReportMessage(FrappeTestCase):
    def test_the_period_alone_with_each_date_left_to_right(self):
        statement = build_statement(
            [opening_row(debit=100), entry_row("SINV-1", debit=300), entry_row("PE-1", credit=120)]
        )

        self.assertEqual(
            report_message(statement, make_header()),
            f'For the period <span dir="ltr">{formatdate(FROM_DATE)}</span>'
            f' to <span dir="ltr">{formatdate(TO_DATE)}</span>:'
            f" total debit: {fmt_money(300.0, currency=CURRENCY)},"
            f" total credit: {fmt_money(120.0, currency=CURRENCY)},"
            f" net: {balance_text(180.0, CURRENCY)}.",
        )

    def test_the_net_takes_its_side_or_none_when_the_period_nets_to_zero(self):
        cases = [
            ("credit", [entry_row("PE-1", credit=50)], balance_text(-50.0, CURRENCY)),
            (
                "nets to zero",
                [entry_row("SINV-1", debit=50), entry_row("PE-1", credit=50)],
                balance_text(0.0, CURRENCY),
            ),
        ]
        for label, rows, net in cases:
            with self.subTest(case=label):
                self.assertTrue(report_message(build_statement(rows), make_header()).endswith(f" net: {net}."))


class TestBand(FrappeTestCase):
    def test_party_period_and_currency(self):
        self.assertEqual(
            band(make_header("Supplier")),
            [
                f"Supplier: {CUSTOMER}",
                f"Statement Period: {formatdate(FROM_DATE)} to {formatdate(TO_DATE)}",
                f"Currency: {CURRENCY}",
            ],
        )


class TestRenderHtml(FrappeTestCase):
    def test_the_page_names_the_company_in_arabic(self):
        header = replace(make_header(), company_name_in_arabic="شركة كشف الحساب")

        self.assertIn("شركة كشف الحساب", render_html(build_statement([]), header))

    def test_the_closing_card_comes_before_the_lines(self):
        html = render_html(build_statement([entry_row("SINV-1", debit=300)]), make_header())

        self.assertLess(html.index("Closing Debit"), html.index('<table class="statement-table"'))


class TestExcelRows(FrappeTestCase):
    def test_the_sheet_reads_like_the_pdf(self):
        statement = build_statement(
            [
                opening_row(credit=20),
                entry_row("SINV-1", debit=100, posting_date="2026-02-01"),
                entry_row("PE-1", credit=150, voucher_type="Payment Entry", posting_date="2026-03-01"),
            ]
        )

        rows = excel_rows(statement, make_header())

        self.assertEqual(rows[0], [COMPANY])
        self.assertEqual(rows[1], ["Statement of Account"])
        self.assertEqual(rows[2], [" | ".join(band(make_header()))])
        self.assertEqual(rows[3], [])
        self.assertEqual(
            rows[4:7], [["Closing Debit", 100.0], ["Closing Credit", 170.0], ["Closing Balance", 70.0, CR]]
        )
        self.assertEqual(rows[7], [])
        self.assertEqual(rows[8], ["Date", "Voucher Type", "Voucher No.", "Debit", "Credit", "Balance", "DR / CR"])
        self.assertEqual(rows[9], [None, "Opening Balance", None, 0.0, 20.0, 20.0, CR])
        self.assertEqual(rows[10], [date(2026, 2, 1), "Sales Invoice", "SINV-1", 100.0, 0.0, 80.0, DR])
        self.assertEqual(rows[11], [date(2026, 3, 1), "Payment Entry", "PE-1", 0.0, 150.0, 70.0, CR])
        self.assertEqual(rows[12:], [[None, "Closing Balance", None, 100.0, 170.0, 70.0, CR]])

    def test_a_settled_balance_leaves_its_side_blank(self):
        rows = excel_rows(build_statement([entry_row("SINV-1", debit=50, credit=50)]), make_header())

        self.assertEqual(rows[6], ["Closing Balance", 0.0, None])
        self.assertEqual(rows[10][-2:], [0.0, None])


class TestFileName(FrappeTestCase):
    def test_the_party_and_end_date_name_the_file(self):
        cases = [
            ("plain", "Al Noor Trading", "Statement-Al Noor Trading-2026-06-30.pdf"),
            ("slash", "Noor/Branch 2", "Statement-Noor-Branch 2-2026-06-30.pdf"),
            ("several unsafe", 'A:B*?"C', "Statement-A-B-C-2026-06-30.pdf"),
            ("arabic", "مؤسسة النور", "Statement-مؤسسة النور-2026-06-30.pdf"),
        ]
        for label, party, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(file_name(party, TO_DATE, "pdf"), expected)

    def test_a_date_object_reads_the_same_as_its_text(self):
        self.assertEqual(file_name(CUSTOMER, date(2026, 6, 30), "xlsx"), file_name(CUSTOMER, TO_DATE, "xlsx"))
