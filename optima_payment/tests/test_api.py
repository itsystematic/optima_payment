"""Focused tests for Optima Payment API helpers."""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.api import get_or_filtered_accounts


class TestOptimaPaymentApi(FrappeTestCase):
    def setUp(self):
        self.company = erpnext.get_default_company()
        self.expense_parent = frappe.db.get_value(
            "Account", {"company": self.company, "root_type": "Expense", "is_group": 1}, "name"
        )
        self.tax_parent = frappe.db.get_value(
            "Account", {"company": self.company, "account_type": "Tax", "is_group": 1}, "name"
        )
        self.asset_parent = frappe.db.get_value(
            "Account", {"company": self.company, "root_type": "Asset", "is_group": 1}, "name"
        )

        if not all([self.company, self.expense_parent, self.tax_parent, self.asset_parent]):
            self.skipTest("The site is missing the account tree required for API search tests.")

    def tearDown(self):
        frappe.db.rollback()

    def test_get_or_filtered_accounts_matches_name_and_account_number(self):
        expense_account = self._make_account(
            account_name="Optima Query Expense Search",
            account_number="OPQ-EXP-001",
            parent_account=self.expense_parent,
        )
        tax_account = self._make_account(
            account_name="Optima Query Tax Search",
            account_number="OPQ-TAX-001",
            parent_account=self.tax_parent,
            account_type="Tax",
        )
        asset_account = self._make_account(
            account_name="Optima Query Asset Search",
            account_number="OPQ-AST-001",
            parent_account=self.asset_parent,
        )

        filters = {"company": self.company, "is_group": 0, "disabled": 0}

        by_name = get_or_filtered_accounts("Account", "Expense Search", "name", 0, 20, filters)
        by_number = get_or_filtered_accounts("Account", "OPQ-TAX-001", "name", 0, 20, filters)
        broad_match = get_or_filtered_accounts("Account", "Optima Query", "name", 0, 20, filters)

        self.assertIn(expense_account.name, [row[0] for row in by_name])
        self.assertIn(tax_account.name, [row[0] for row in by_number])
        self.assertNotIn(asset_account.name, [row[0] for row in broad_match])

    def test_get_or_filtered_accounts_applies_pagination(self):
        self._make_account(
            account_name="Optima Pagination Expense One",
            account_number="OPQ-PAG-001",
            parent_account=self.expense_parent,
        )
        self._make_account(
            account_name="Optima Pagination Expense Two",
            account_number="OPQ-PAG-002",
            parent_account=self.expense_parent,
        )

        filters = {"company": self.company, "is_group": 0, "disabled": 0}

        first_page = get_or_filtered_accounts("Account", "Optima Pagination Expense", "name", 0, 1, filters)
        second_page = get_or_filtered_accounts("Account", "Optima Pagination Expense", "name", 1, 1, filters)

        self.assertEqual(len(first_page), 1)
        self.assertEqual(len(second_page), 1)
        self.assertNotEqual(first_page[0][0], second_page[0][0])

    def _make_account(self, account_name, account_number, parent_account, account_type=None):
        account = frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": account_name,
                "account_number": account_number,
                "parent_account": parent_account,
                "company": self.company,
                "is_group": 0,
                "account_type": account_type,
            }
        )
        account.insert()
        return account
