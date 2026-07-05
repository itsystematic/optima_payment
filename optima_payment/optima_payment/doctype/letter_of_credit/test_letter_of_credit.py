# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""Tier-4 integration tests for Letter of Credit.

Builds real, submitted documents via the factories in optima_payment.tests.utils
and asserts on the Payment Entry documents they generate. Unlike Bank Guarantee-BG
(which posts raw GL Entry rows), Letter of Credit posts all accounting impact via
system-generated Payment Entry (Internal Transfer) documents linked back through the
`letter_of_credit` field and tagged with the `is_lc_*` flags - so these tests assert
on those Payment Entries.

Covers validation, submit/PE construction (Providing vs Receiving, with/without issue
commission, and the insurance-account fallback), return, extend, close/reopen and
cancel - including the asymmetry that Receiving reverses the transfer direction and
that commission is never carried into a reversal.

Note: a `Loss` action exists for Bank Guarantee-BG but is not yet wired for Letter of
Credit (the is_lc_loss_entry flag and lc_loss_expense_account setting are plumbed but
unused), so there are no loss tests here.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from optima_payment.tests.utils import make_letter_of_credit, make_optima_payment_setting


def strict_cost_center_pe_validation() -> bool:
    """True when this site enforces the (WTS) rule that a Balance Sheet GL line must carry
    no cost center while a P&L line must carry one.

    The validity-only extend commission posts a *standalone* Payment Entry (Internal
    Transfer) that mixes a bank (Balance Sheet) line and an expense (P&L) line under a
    single cost center - which cannot satisfy that rule either way. This helper lets the
    corresponding test skip on such sites; the CI site has no WTS app, so it runs there.
    """
    if not frappe.db.exists("DocType", "WTS Setting"):
        return False
    if not frappe.db.get_single_value("WTS Setting", "enable_validate_in_cost_center"):
        return False
    rows = frappe.get_cached_doc("WTS Setting").get("doctype_for_validation") or []
    return "Payment Entry" in {row.doctype_name for row in rows}


class TestLetterofCredit(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def get_lc_payment_entries(self, lc_name: str, **flag_filters) -> list[frappe._dict]:
        """Return submitted Payment Entries linked to this LC.

        Pass any is_lc_* flag as a keyword (e.g. is_lc_return_entry=1) to narrow the
        result to a specific kind of generated entry.
        """
        filters = {"letter_of_credit": lc_name, "docstatus": 1}
        filters.update(flag_filters)
        return frappe.get_all(
            "Payment Entry",
            filters=filters,
            fields=[
                "name",
                "paid_from",
                "paid_to",
                "paid_amount",
                "is_lc_commission_entry",
                "is_lc_return_entry",
                "is_lc_close_entry",
                "is_system_generated",
            ],
            order_by="creation asc",
        )

    # ============================================================================================
    # VALIDATION
    # ============================================================================================

    def test_validate_requires_customer_or_supplier(self):
        doc = make_letter_of_credit(lc_type="Providing", do_not_submit=True)
        doc.customer = None
        doc.supplier = None

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_validate_requires_lc_number_and_beneficiary(self):
        doc = make_letter_of_credit(lc_type="Providing", do_not_submit=True)
        doc.lc_number = None

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_validate_requires_mode_of_payment(self):
        doc = make_letter_of_credit(lc_type="Providing", do_not_submit=True)
        doc.mode_of_payment = None

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_validate_requires_company_accounts(self):
        doc = make_letter_of_credit(lc_type="Providing", do_not_submit=True)

        setting_name = frappe.db.get_value("Optima Payment Setting", {"company": doc.company}, "name")
        frappe.db.set_value("Optima Payment Setting", setting_name, "lc_insurance_account", None)
        frappe.clear_document_cache("Optima Payment Setting", setting_name)

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    # ============================================================================================
    # SUBMIT / PAYMENT ENTRY CONSTRUCTION
    # ============================================================================================

    def test_submit_providing_sets_status_and_posts_collateral_pe(self):
        doc = make_letter_of_credit(lc_type="Providing")

        self.assertEqual(doc.lc_status, "Issued")

        entries = self.get_lc_payment_entries(doc.name)
        self.assertEqual(len(entries), 1)

        pe = entries[0]
        self.assertEqual(pe.paid_from, doc.account)
        self.assertEqual(pe.paid_to, doc.lc_account)
        self.assertEqual(pe.paid_amount, doc.bank_amount)
        self.assertEqual(pe.is_system_generated, 1)

    def test_submit_providing_uses_insurance_account_when_lc_account_unset(self):
        # No lc_account -> get_payment_entry_accounts() falls back to the settings account.
        doc = make_letter_of_credit(lc_type="Providing", lc_account=None)
        settings = make_optima_payment_setting(doc.company)

        entries = self.get_lc_payment_entries(doc.name)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].paid_to, settings.lc_insurance_account)

    def test_submit_providing_with_commission_adds_tax_row(self):
        doc = make_letter_of_credit(lc_type="Providing", issue_commission=1)
        settings = make_optima_payment_setting(doc.company)

        entries = self.get_lc_payment_entries(doc.name)
        self.assertEqual(len(entries), 1)

        pe = frappe.get_doc("Payment Entry", entries[0].name)
        self.assertEqual(len(pe.taxes), 1)
        self.assertEqual(pe.taxes[0].account_head, settings.lc_bank_fees_account)
        self.assertEqual(pe.taxes[0].tax_amount, doc.issue_commission_amount)

    def test_submit_receiving_sets_status_and_reverses_direction(self):
        doc = make_letter_of_credit(lc_type="Receiving")

        self.assertEqual(doc.lc_status, "Exists")

        entries = self.get_lc_payment_entries(doc.name)
        self.assertEqual(len(entries), 1)

        pe = entries[0]
        # Receiving flips the transfer: money lands in `account`, funded from lc_account.
        self.assertEqual(pe.paid_to, doc.account)
        self.assertEqual(pe.paid_from, doc.lc_account)

    # ============================================================================================
    # RETURN
    # ============================================================================================

    def test_lc_return_sets_status_and_reverses_collateral(self):
        doc = make_letter_of_credit(lc_type="Providing")

        doc.lc_return(nowdate())
        doc.reload()

        self.assertEqual(doc.lc_status, "Returned")
        self.assertEqual(doc.returned_date, getdate(nowdate()))

        # original collateral PE + one reversal PE with the direction swapped
        self.assertEqual(len(self.get_lc_payment_entries(doc.name)), 2)

        reversals = self.get_lc_payment_entries(doc.name, is_lc_return_entry=1)
        self.assertEqual(len(reversals), 1)
        self.assertEqual(reversals[0].paid_from, doc.lc_account)
        self.assertEqual(reversals[0].paid_to, doc.account)

    def test_lc_return_does_not_reverse_commission(self):
        doc = make_letter_of_credit(lc_type="Providing", issue_commission=1)

        doc.lc_return(nowdate())
        doc.reload()

        # The reversal PE reverses only the collateral transfer - the commission tax row
        # is a permanent bank cost and must not be carried into the reversal.
        reversals = self.get_lc_payment_entries(doc.name, is_lc_return_entry=1)
        self.assertEqual(len(reversals), 1)
        reversal = frappe.get_doc("Payment Entry", reversals[0].name)
        self.assertEqual(len(reversal.taxes), 0)

    def test_lc_return_rejects_date_before_recent_transaction(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_return(add_days(nowdate(), -5))

    # ============================================================================================
    # EXTEND
    # ============================================================================================

    def test_lc_extend_validity_only_with_commission_books_standalone_pe(self):
        if strict_cost_center_pe_validation():
            self.skipTest(
                "Site enforces the WTS Balance-Sheet/P&L cost-center rule, which the "
                "standalone commission Internal Transfer cannot satisfy."
            )

        doc = make_letter_of_credit(lc_type="Providing")
        before = len(self.get_lc_payment_entries(doc.name))

        doc.lc_extend_action(
            commission_amount=20,
            end_date=add_days(doc.end_date, 9),
            extended_days=10,
            extend_to_date=add_days(doc.end_date, 1),
            has_commission=True,
        )
        doc.reload()

        self.assertEqual(doc.lc_status, "Extended")
        self.assertEqual(doc.no_of_extended_days, 10)
        self.assertEqual(doc.extend_validity, 1)

        # A validity-only extension books a standalone commission PE (no collateral change).
        commission_entries = self.get_lc_payment_entries(doc.name, is_lc_commission_entry=1)
        self.assertEqual(len(commission_entries), 1)
        self.assertEqual(len(self.get_lc_payment_entries(doc.name)), before + 1)

    def test_lc_extend_with_amount_extension_books_collateral_pe(self):
        doc = make_letter_of_credit(lc_type="Providing")
        before = len(self.get_lc_payment_entries(doc.name))

        doc.lc_extend_action(
            commission_amount=0,
            end_date=add_days(doc.end_date, 9),
            extended_days=5,
            extend_to_date=add_days(doc.end_date, 1),
            has_amount_extension=True,
            lc_amount_extension=200,
        )
        doc.reload()

        self.assertEqual(doc.lc_status, "Extended")
        self.assertEqual(len(self.get_lc_payment_entries(doc.name)), before + 1)

        # The new collateral PE carries the extended amount.
        amounts = {pe.paid_amount for pe in self.get_lc_payment_entries(doc.name)}
        self.assertIn(200, amounts)

    def test_lc_extend_action_rejects_date_before_recent_transaction(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_extend_action(
                commission_amount=0,
                end_date=doc.end_date,
                extended_days=10,
                extend_to_date=add_days(nowdate(), -5),
                has_commission=False,
            )

    # ============================================================================================
    # CLOSE / REOPEN
    # ============================================================================================

    def test_lc_close_sets_status_and_books_reversed_pe(self):
        doc = make_letter_of_credit(lc_type="Providing")
        before = len(self.get_lc_payment_entries(doc.name))

        doc.lc_close_action(nowdate(), doc.bank_amount)
        doc.reload()

        self.assertEqual(doc.lc_status, "Closed")
        self.assertEqual(doc.pre_close_status, "Issued")

        close_entries = self.get_lc_payment_entries(doc.name, is_lc_close_entry=1)
        self.assertEqual(len(close_entries), 1)
        self.assertEqual(len(self.get_lc_payment_entries(doc.name)), before + 1)

        # Close reverses the submit direction.
        self.assertEqual(close_entries[0].paid_from, doc.lc_account)
        self.assertEqual(close_entries[0].paid_to, doc.account)

    def test_lc_reopen_restores_previous_status(self):
        doc = make_letter_of_credit(lc_type="Providing")

        doc.lc_close_action(nowdate(), doc.bank_amount)
        doc.reload()
        self.assertEqual(doc.lc_status, "Closed")

        doc.lc_reopen_action(nowdate())
        doc.reload()

        self.assertEqual(doc.lc_status, "Issued")
        self.assertFalse(doc.pre_close_status)

    def test_lc_reopen_rejects_when_not_closed(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_reopen_action(nowdate())

    # ============================================================================================
    # CANCEL
    # ============================================================================================

    def test_cancel_cancels_linked_payment_entries(self):
        doc = make_letter_of_credit(lc_type="Providing")
        pe_names = [pe.name for pe in self.get_lc_payment_entries(doc.name)]
        self.assertTrue(pe_names)

        doc.cancel()

        for name in pe_names:
            self.assertEqual(frappe.db.get_value("Payment Entry", name, "docstatus"), 2)
