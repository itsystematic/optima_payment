# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The statement of account through the real General Ledger, report and API.

The branch matrix is in test_statement.py. These prove what only real vouchers show: the Opening row,
the entries and the Closing row equal the site's own General Ledger for the same party (ERPNext's, or
the copy an app swaps in, whose Opening keeps debit and credit apart), the report returns its
summary cards, the API refuses other party types and users who can't open the report, an Accounts
User gets the print page naming the company and the party, and the Excel download is a real xlsx.
"""

import erpnext
import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, getdate, nowdate

from optima_payment.optima_payment.report.customer_statement.customer_statement import execute
from optima_payment.party_statement import api
from optima_payment.party_statement.statement import general_ledger, get_statement, gl_filters
from optima_payment.tests.utils import (
    get_or_create_customer,
    get_or_create_supplier,
    get_or_create_user,
    make_party_journal_entry,
)


class TestPartyStatementIntegration(FrappeTestCase):
    def setUp(self):
        self.company = erpnext.get_default_company()
        self.customer = get_or_create_customer("Optima Statement Customer")
        self.supplier = get_or_create_supplier("Optima Statement Supplier")

        # Every date sits in one fiscal year, which the Journal Entries need. The period is text, as a
        # request sends it to the whitelisted methods.
        _fiscal_year, year_start, year_end = get_fiscal_year(nowdate(), company=self.company)
        self.before_period = getdate(year_start)
        self.from_date = str(add_days(year_start, 1))
        self.to_date = str(getdate(year_end))

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def statement(self, party_type, party):
        return get_statement(party_type, party, self.company, self.from_date, self.to_date)

    def general_ledger_rows(self, party_type, party):
        _columns, rows = general_ledger(gl_filters(party_type, party, self.company, self.from_date, self.to_date))
        return rows

    def ledger_side(self, row) -> tuple[float, float]:
        return flt(row.debit, 2), flt(row.credit, 2)

    def make_customer_vouchers(self):
        """100 owed and 40 paid before the period, then 30 paid and 50 more owed inside it.

        The opening is 60 DR, which ERPNext's ledger shows as 60 / 0 and the copies apps swap in as
        100 / 40. The closing is 80 DR.
        """
        make_party_journal_entry(
            party_type="Customer", party=self.customer, amount=100, posting_date=self.before_period
        )
        make_party_journal_entry(
            party_type="Customer", party=self.customer, amount=-40, posting_date=self.before_period
        )
        paid = make_party_journal_entry(
            party_type="Customer", party=self.customer, amount=-30, posting_date=self.from_date
        )
        owed = make_party_journal_entry(
            party_type="Customer", party=self.customer, amount=50, posting_date=self.from_date
        )
        return paid, owed

    def test_the_statement_matches_the_general_ledger(self):
        paid, owed = self.make_customer_vouchers()

        statement, header = self.statement("Customer", self.customer)
        ledger = self.general_ledger_rows("Customer", self.customer)
        ledger_opening, ledger_closing = ledger[0], ledger[-1]

        self.assertEqual((statement.opening_debit, statement.opening_credit), self.ledger_side(ledger_opening))
        self.assertEqual(statement.opening, 60.0)
        self.assertEqual(
            [(entry.voucher_no, entry.debit, entry.credit, entry.balance) for entry in statement.entries],
            [(paid.name, 0.0, 30.0, 30.0), (owed.name, 50.0, 0.0, 80.0)],
        )
        self.assertEqual(
            [entry.voucher_no for entry in statement.entries], [row.voucher_no for row in ledger if row.voucher_no]
        )
        self.assertEqual((statement.closing_debit, statement.closing_credit), self.ledger_side(ledger_closing))
        self.assertEqual(statement.closing, 80.0)
        self.assertEqual(header.currency, frappe.get_cached_value("Company", self.company, "default_currency"))

    def test_a_supplier_owed_money_reads_as_credit(self):
        bill = make_party_journal_entry(
            party_type="Supplier", party=self.supplier, amount=-75, posting_date=self.from_date
        )

        statement, header = self.statement("Supplier", self.supplier)

        self.assertEqual([entry.voucher_no for entry in statement.entries], [bill.name])
        self.assertEqual(statement.closing, -75.0)
        self.assertEqual(header.party_name, frappe.db.get_value("Supplier", self.supplier, "supplier_name"))

    def test_the_report_returns_its_rows_and_summary_cards(self):
        self.make_customer_vouchers()

        columns, rows, _message, _chart, summary = execute(
            {
                "company": self.company,
                "party": self.customer,
                "from_date": self.from_date,
                "to_date": self.to_date,
            }
        )

        self.assertEqual(
            [column["fieldname"] for column in columns],
            ["posting_date", "voucher_type", "voucher_no", "debit", "credit", "balance"],
        )
        self.assertEqual([row["balance"] for row in rows], [60.0, 30.0, 80.0, 80.0])
        self.assertEqual([row["indicator"] for row in rows], ["Green"] * 4)

        closing_row = rows[-1]
        closing_debit, closing_credit, closing_balance, separator, debit, credit, _net = summary
        self.assertEqual(
            (closing_debit["value"], closing_credit["value"]), (closing_row["debit"], closing_row["credit"])
        )
        self.assertEqual(closing_balance["indicator"], "Green")
        self.assertEqual(separator["type"], "separator")
        self.assertEqual((debit["value"], credit["value"]), (50.0, 30.0))

    def test_the_api_refuses_a_party_type_other_than_customer_or_supplier(self):
        with self.assertRaises(frappe.ValidationError):
            api.get_preview_html("Employee", "HR-EMP-00001", self.company, self.from_date, self.to_date)

    def test_the_api_refuses_a_user_who_cannot_open_the_report(self):
        # Sales User reads customers but holds none of the statement report's roles.
        frappe.set_user(get_or_create_user("optima.statement.sales@example.com", ["Sales User"]))

        with self.assertRaises(frappe.PermissionError):
            api.get_preview_html("Customer", self.customer, self.company, self.from_date, self.to_date)

    def test_an_accounts_user_gets_the_page_naming_the_company_and_the_party(self):
        self.make_customer_vouchers()
        # Sites may take Customer read away from Accounts User; Sales User grants it everywhere, and
        # Accounts User alone opens the report.
        frappe.set_user(
            get_or_create_user("optima.statement.accounts@example.com", ["Accounts User", "Sales User"])
        )

        html = api.get_preview_html("Customer", self.customer, self.company, self.from_date, self.to_date)

        self.assertIn('class="print-format"', html)
        self.assertIn(self.company, html)
        self.assertIn(self.customer, html)

    def test_the_excel_download_is_an_xlsx_named_for_the_party(self):
        self.make_customer_vouchers()

        api.download_excel("Customer", self.customer, self.company, self.from_date, self.to_date)

        response = frappe.local.response
        self.assertEqual(response.type, "download")
        self.assertEqual(response.filename, f"Statement-{self.customer}-{self.to_date}.xlsx")
        self.assertTrue(response.filecontent.startswith(b"PK"))
