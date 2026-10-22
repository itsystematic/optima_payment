# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The branch matrix for the statement of account. Nothing here writes to the database.

Rows are ``frappe._dict`` objects shaped like the General Ledger's, so no party or voucher has to
exist on the site. The wiring through the real ledger is in test_statement_integration.py.
"""

import math
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate, getdate

from optima_payment.party_statement.statement import (
    CR,
    DR,
    Statement,
    StatementHeader,
    band,
    build_statement,
    dr_cr,
    excel_rows,
    file_name,
    gl_filters,
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
                "include_default_book_entries": 1,
                "show_opening_entries": 0,
            },
        )

    def test_the_currency_is_left_to_the_ledger(self):
        self.assertNotIn("presentation_currency", gl_filters("Customer", CUSTOMER, COMPANY, FROM_DATE, TO_DATE))


class TestBuildStatement(FrappeTestCase):
    def test_an_empty_period_keeps_the_opening_as_the_closing(self):
        statement = build_statement([opening_row(debit=250), *trailing_rows()])

        self.assertEqual(
            statement,
            Statement(opening=250.0, entries=[], total_debit=0.0, total_credit=0.0, closing=250.0),
        )

    def test_a_party_with_no_ledger_rows_is_all_zero(self):
        cases = [
            ("no rows at all", []),
            ("zero opening and no entries", [opening_row(), *trailing_rows()]),
        ]
        for label, rows in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    build_statement(rows),
                    Statement(opening=0.0, entries=[], total_debit=0.0, total_credit=0.0, closing=0.0),
                )

    def test_a_credit_opening_is_negative(self):
        self.assertEqual(build_statement([opening_row(credit=80)]).opening, -80.0)

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
        """The ledger has summed an opening of 2.2737e-13 CR on a real site; it must read 0.00 DR."""
        statement = build_statement([opening_row(credit=2.2737367544323206e-13)])

        self.assertEqual(statement.opening, 0.0)
        self.assertEqual(math.copysign(1, statement.opening), 1.0)

    def test_amounts_round_to_the_given_precision(self):
        statement = build_statement([entry_row("SINV-1", debit=10.006)], precision=2)

        self.assertEqual(statement.entries[0].debit, 10.01)


class TestDrCr(FrappeTestCase):
    def test_the_sign_picks_the_side_and_zero_reads_as_dr(self):
        cases = [
            ("debit", 24495.0, (24495.0, DR)),
            ("credit", -27324.45, (27324.45, CR)),
            ("zero", 0.0, (0.0, DR)),
            ("negative zero", -0.0, (0.0, DR)),
        ]
        for label, amount, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(dr_cr(amount), expected)


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


class TestReportRows(FrappeTestCase):
    def setUp(self):
        self.statement = build_statement(
            [opening_row(debit=100), entry_row("PE-1", credit=150, voucher_type="Payment Entry")]
        )

    def test_bold_opening_and_closing_rows_frame_the_entries(self):
        rows = report_rows(self.statement, CURRENCY)

        self.assertEqual(
            rows[0], {"voucher_type": "Opening Balance", "balance": 100.0, "currency": CURRENCY, "bold": 1}
        )
        self.assertEqual(
            rows[-1], {"voucher_type": "Closing Balance", "balance": -50.0, "currency": CURRENCY, "bold": 1}
        )
        self.assertEqual([row["voucher_no"] for row in rows[1:-1]], ["PE-1"])

    def test_entries_keep_a_signed_balance_and_carry_the_currency(self):
        entry = report_rows(self.statement, CURRENCY)[1]

        self.assertEqual((entry["balance"], entry["currency"]), (-50.0, CURRENCY))
        self.assertNotIn("bold", entry)


class TestReportSummary(FrappeTestCase):
    def test_three_cards_with_the_outstanding_side(self):
        statement = build_statement([opening_row(), entry_row("SINV-1", debit=300), entry_row("PE-1", credit=100)])

        debit, credit, outstanding = report_summary(statement, CURRENCY)

        self.assertEqual(
            (debit["label"], debit["value"], debit["datatype"], debit["currency"]),
            ("Total Debit", 300.0, "Currency", CURRENCY),
        )
        self.assertEqual((credit["label"], credit["value"]), ("Total Credit", 100.0))
        self.assertEqual(outstanding["label"], "Outstanding Balance")
        self.assertTrue(outstanding["value"].endswith("200.00 DR"), outstanding["value"])

    def test_the_outstanding_card_is_red_for_dr_and_green_for_cr(self):
        cases = [
            ("owes the company", [entry_row("SINV-1", debit=10)], "Red"),
            ("settled", [], "Red"),
            ("in credit", [entry_row("PE-1", credit=10)], "Green"),
        ]
        for label, rows, indicator in cases:
            with self.subTest(case=label):
                outstanding = report_summary(build_statement(rows), CURRENCY)[2]
                self.assertEqual(outstanding["indicator"], indicator)


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
        self.assertEqual(rows[4], ["Date", "Voucher Type", "Voucher No.", "Debit", "Credit", "Balance", "DR / CR"])
        self.assertEqual(rows[5], [None, "Opening Balance", None, None, None, 20.0, CR])
        self.assertEqual(rows[6], [date(2026, 2, 1), "Sales Invoice", "SINV-1", 100.0, 0.0, 80.0, DR])
        self.assertEqual(rows[7], [date(2026, 3, 1), "Payment Entry", "PE-1", 0.0, 150.0, 70.0, CR])
        self.assertEqual(rows[8], [None, "Closing Balance", None, None, None, 70.0, CR])
        self.assertEqual(rows[9], [])
        self.assertEqual(
            rows[10:],
            [["Total Debit", 100.0], ["Total Credit", 150.0], ["Outstanding Balance", 70.0, CR]],
        )


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
