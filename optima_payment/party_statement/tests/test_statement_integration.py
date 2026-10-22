# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The statement of account through the real General Ledger, report and API.

The branch matrix is in test_statement.py. These prove what only real vouchers show: the opening,
the entries and the closing agree with the General Ledger for the same party, the report returns its
summary cards, the API refuses other party types and users who can't open the report, an Accounts
User gets the print page naming the company and the party, and the Excel download is a real xlsx.
"""

import erpnext
import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute as general_ledger
from erpnext.accounts.utils import get_fiscal_year
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from optima_payment.optima_payment.report.customer_statement.customer_statement import execute
from optima_payment.party_statement import api
from optima_payment.party_statement.statement import gl_filters, get_statement
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

    def make_customer_vouchers(self):
        """100 owed before the period, then 30 paid and 50 more owed inside it: 120 DR at the end."""
        make_party_journal_entry(
            party_type="Customer", party=self.customer, amount=100, posting_date=self.before_period
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

        self.assertEqual(statement.opening, 100.0)
        self.assertEqual(statement.opening, ledger_opening.debit - ledger_opening.credit)
        self.assertEqual(
            [(entry.voucher_no, entry.debit, entry.credit, entry.balance) for entry in statement.entries],
            [(paid.name, 0.0, 30.0, 70.0), (owed.name, 50.0, 0.0, 120.0)],
        )
        self.assertEqual(
            [entry.voucher_no for entry in statement.entries], [row.voucher_no for row in ledger if row.voucher_no]
        )
        self.assertEqual(statement.closing, 120.0)
        self.assertEqual(statement.closing, ledger_closing.debit - ledger_closing.credit)
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
        self.assertEqual([row["balance"] for row in rows], [100.0, 70.0, 120.0, 120.0])
        self.assertEqual([card["value"] for card in summary[:2]], [50.0, 30.0])
        self.assertEqual(summary[2]["indicator"], "Red")

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
