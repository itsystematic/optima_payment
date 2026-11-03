# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The Time Based Overdue Limit through real saves and submits of Sales Invoices and Sales Orders.

The branch matrix and the message text are in test_limit.py. These prove what only a real document
shows: each action is checked at its own hook on both doctypes (Warn on Save at validate, so at
submit too; Block on Save at before_save only; Block on Submit at before_submit only), the acting
user's roles decide the exemption, credit notes pass, the group tree is read from the database, and
only a payment allocated to the invoice lifts the block.

Each test starts from a customer whose Sales Invoice fell due 25 days ago and that ERPNext's daily
status job has marked Overdue.
"""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.overdue_limit.limit import BLOCK_ON_SAVE, BLOCK_ON_SUBMIT, WARN_ON_SAVE, OverdueLimitError
from optima_payment.tests.utils import (
    get_or_create_customer,
    get_or_create_user,
    make_credit_note,
    make_invoice_overdue,
    make_invoice_payment,
    make_overdue_limit,
    make_sales_invoice,
    make_sales_order,
)

CUSTOMER = "Optima Overdue Test Customer"
SALES_ROLES = ["Sales User", "Sales Manager", "Accounts User"]
EXEMPT_ROLE = "Accounts Manager"
SALES_DOCUMENTS = {"Sales Invoice": make_sales_invoice, "Sales Order": make_sales_order}


class TestOverdueLimitIntegration(FrappeTestCase):
    def setUp(self):
        self.company = erpnext.get_default_company()
        self.customer = get_or_create_customer(CUSTOMER)
        self.overdue_invoice = make_sales_invoice(customer=self.customer)
        make_invoice_overdue(self.overdue_invoice.name, days=25)
        frappe.clear_messages()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def make_draft(self, doctype="Sales Invoice"):
        return SALES_DOCUMENTS[doctype](customer=self.customer, do_not_submit=True)

    def overdue_messages(self) -> list:
        return [msg for msg in frappe.get_message_log() if self.overdue_invoice.name in msg.message]

    def act_as(self, email, roles):
        frappe.set_user(get_or_create_user(email, roles))

    def submit(self, doc):
        doc.flags.ignore_permissions = True
        doc.submit()

    # ============================================================================================
    # ACTIONS

    def test_warn_on_save_saves_the_draft_with_a_warning(self):
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE)
        for doctype in SALES_DOCUMENTS:
            with self.subTest(doctype):
                frappe.clear_messages()
                draft = self.make_draft(doctype)
                self.assertFalse(draft.is_new())
                self.assertTrue(self.overdue_messages())

    def test_warn_on_save_warns_again_at_submit(self):
        """Frappe runs validate at submit too."""
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE)
        draft = self.make_draft()
        frappe.clear_messages()
        self.submit(draft)
        self.assertEqual(draft.docstatus, 1)
        self.assertTrue(self.overdue_messages())

    def test_block_on_save_refuses_the_draft(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        for doctype in SALES_DOCUMENTS:
            with self.subTest(doctype), self.assertRaises(OverdueLimitError):
                self.make_draft(doctype)

    def test_block_on_save_lets_a_draft_saved_before_the_rule_submit(self):
        draft = self.make_draft()
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        self.submit(draft)
        self.assertEqual(draft.docstatus, 1)

    def test_block_on_submit_saves_the_draft_silently_and_refuses_the_submit(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SUBMIT)
        for doctype in SALES_DOCUMENTS:
            with self.subTest(doctype):
                frappe.clear_messages()
                draft = self.make_draft(doctype)
                self.assertFalse(self.overdue_messages())
                with self.assertRaises(OverdueLimitError):
                    self.submit(draft)

    # ============================================================================================
    # WHO AND WHAT IS LET THROUGH

    def test_the_acting_users_roles_decide_the_exemption(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE, exempt_roles=[EXEMPT_ROLE])

        self.act_as("optima.overdue.sales@example.com", SALES_ROLES)
        with self.assertRaises(OverdueLimitError):
            self.make_draft()

        self.act_as("optima.overdue.exempt@example.com", [*SALES_ROLES, EXEMPT_ROLE])
        draft = self.make_draft()
        self.submit(draft)
        self.assertEqual(draft.docstatus, 1)

    def test_a_credit_note_saves_and_submits_under_both_blocks(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SUBMIT)
        credit_note = make_credit_note(self.overdue_invoice.name)
        credit_note.insert(ignore_permissions=True)
        self.submit(credit_note)
        self.assertEqual(credit_note.docstatus, 1)

    def test_a_rule_on_an_ancestor_group_applies(self):
        group = frappe.db.get_value("Customer", self.customer, "customer_group")
        parent_group = frappe.db.get_value("Customer Group", group, "parent_customer_group")
        make_overdue_limit(applies_to="Customer Group", party=parent_group, action=BLOCK_ON_SAVE)
        with self.assertRaises(OverdueLimitError):
            self.make_draft()

    def test_a_rule_for_another_company_does_not_apply(self):
        other_company = frappe.db.get_value("Company", {"name": ("!=", self.company)}, "name")
        if not other_company:
            self.skipTest("the site has a single company")

        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE, company=other_company)
        self.assertFalse(self.make_draft().is_new())

    # ============================================================================================
    # LIFTING THE BLOCK

    def test_paying_the_overdue_invoice_lifts_the_block(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        make_invoice_payment(self.overdue_invoice.name)
        self.assertFalse(self.make_draft().is_new())

    def test_an_unallocated_payment_covering_the_debt_keeps_the_block(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        make_invoice_payment(self.overdue_invoice.name, allocate=False)
        with self.assertRaises(OverdueLimitError):
            self.make_draft()

    def test_a_disabled_rule_does_nothing(self):
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE, enabled=0)
        self.assertFalse(self.make_draft().is_new())
        self.assertFalse(self.overdue_messages())
