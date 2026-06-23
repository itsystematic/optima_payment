# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""Tier-4 integration tests for Bank Guarantee-BG.

Builds real, submitted documents via the factories in optima_payment.tests.utils
and asserts on the GL Entry rows they produce, following the
get_gle/validate_gl_entries pattern used by ERPNext's own
test_payment_entry.py. Covers GL construction on submit (Providing vs
Receiving, with/without issue commission), cancel, return, extend, and loss,
including the asymmetry that Receiving guarantees post no GL on submit and
that commission rows are excluded from reversal.
"""

import frappe
from frappe.utils import add_days, nowdate
from frappe.tests.utils import FrappeTestCase

from optima_payment.tests.utils import make_bank_guarantee_bg, make_optima_payment_setting


class TestBankGuaranteeBG(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def get_gle(self, voucher_no, include_cancelled=False):
        gl_entries = frappe.db.sql(
            """select account, debit, credit, is_cancelled, is_bank_guarantee_comission_entry
               from `tabGL Entry` where voucher_type='Bank Guarantee-BG' and voucher_no=%s
               order by account asc, debit asc""",
            voucher_no,
            as_dict=1,
        )
        if include_cancelled:
            return gl_entries
        return [gle for gle in gl_entries if not gle.is_cancelled]

    def validate_gl_entries(self, voucher_no, expected_gle):
        """expected_gle: set of (account, debit, credit) tuples."""
        gl_entries = self.get_gle(voucher_no)
        actual = {(gle.account, gle.debit, gle.credit) for gle in gl_entries}
        self.assertEqual(actual, expected_gle)

    # ============================================================================================
    # SUBMIT / GL CONSTRUCTION
    # ============================================================================================

    def test_submit_providing_creates_bank_and_guarantee_gl_rows(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")
        settings = make_optima_payment_setting(doc.company)

        self.validate_gl_entries(
            doc.name,
            {
                (settings.bank_guarantee_insurance_account, doc.bank_amount, 0),
                (doc.account, 0, doc.bank_amount),
            },
        )

    def test_submit_providing_with_commission_books_commission_gl_rows(self):
        doc = make_bank_guarantee_bg(bg_type="Providing", issue_commission=1)
        settings = make_optima_payment_setting(doc.company)

        self.validate_gl_entries(
            doc.name,
            {
                (settings.bank_guarantee_insurance_account, doc.bank_amount, 0),
                (doc.account, 0, doc.bank_amount),
                (settings.bank_guarantee_bank_fees_account, doc.issue_commission_amount, 0),
                (doc.account, 0, doc.issue_commission_amount),
            },
        )

    def test_submit_receiving_creates_no_gl_entries(self):
        doc = make_bank_guarantee_bg(bg_type="Receiving")

        self.assertEqual(self.get_gle(doc.name), [])
        self.assertEqual(doc.bank_guarantee_status, "Exists")

    # ============================================================================================
    # CANCEL
    # ============================================================================================

    def test_cancel_reverses_gl_entries(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")
        doc.cancel()

        active_entries = self.get_gle(doc.name)
        all_entries = self.get_gle(doc.name, include_cancelled=True)

        self.assertEqual(active_entries, [])
        self.assertTrue(all(gle.is_cancelled for gle in all_entries))

    # ============================================================================================
    # RETURN
    # ============================================================================================

    def test_bank_guarantee_return_sets_status_and_reverses_gl(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")

        doc.bank_guarantee_return(nowdate())
        doc.reload()

        self.assertEqual(doc.bank_guarantee_status, "Returned")
        self.assertEqual(doc.returned_date, frappe.utils.getdate(nowdate()))

        # original 2 rows + 2 reversal rows with debit/credit swapped
        self.assertEqual(len(self.get_gle(doc.name)), 4)

    def test_bank_guarantee_return_skips_commission_entries_on_reversal(self):
        doc = make_bank_guarantee_bg(bg_type="Providing", issue_commission=1)

        doc.bank_guarantee_return(nowdate())
        doc.reload()

        # original 4 (2 main + 2 commission) + 2 reversal rows for the main entries only
        self.assertEqual(len(self.get_gle(doc.name)), 6)

    def test_bank_guarantee_return_rejects_date_before_last_transaction(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.bank_guarantee_return(add_days(nowdate(), -5))

    # ============================================================================================
    # EXTEND
    # ============================================================================================

    def test_make_extend_action_with_commission_books_commission_gl(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")
        before = len(self.get_gle(doc.name))
        extend_to_date = add_days(doc.end_date, 1)

        doc.make_extend_action(
            amount=20,
            end_date=add_days(doc.end_date, 9),
            days=10,
            extend_to_date=extend_to_date,
            has_commission=True,
        )
        doc.reload()

        self.assertEqual(doc.bank_guarantee_status, "Extended")
        self.assertEqual(doc.no_of_extended_days, 10)
        self.assertEqual(doc.extend_validity, 1)

        # 2 new rows for the extend commission
        self.assertEqual(len(self.get_gle(doc.name)), before + 2)

    def test_make_extend_action_without_commission_skips_gl(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")
        before = len(self.get_gle(doc.name))
        extend_to_date = add_days(doc.end_date, 1)

        doc.make_extend_action(
            amount=0,
            end_date=add_days(doc.end_date, 9),
            days=10,
            extend_to_date=extend_to_date,
            has_commission=False,
        )
        doc.reload()

        self.assertEqual(doc.bank_guarantee_status, "Extended")
        self.assertEqual(len(self.get_gle(doc.name)), before)

    # ============================================================================================
    # LOSS
    # ============================================================================================

    def test_make_loss_action_providing_reverses_original_and_books_loss_gl(self):
        doc = make_bank_guarantee_bg(bg_type="Providing")

        doc.make_loss_action(nowdate())
        doc.reload()

        self.assertEqual(doc.bank_guarantee_status, "Lost")

        # original 2 + reversal 2 + new loss pair 2
        self.assertEqual(len(self.get_gle(doc.name)), 6)

    def test_make_loss_action_receiving_books_loss_gl(self):
        doc = make_bank_guarantee_bg(bg_type="Receiving")
        settings = make_optima_payment_setting(doc.company)

        doc.make_loss_action(nowdate())
        doc.reload()

        self.assertEqual(doc.bank_guarantee_status, "Lost")

        # no original GL existed for Receiving on submit, so only the new loss pair
        self.validate_gl_entries(
            doc.name,
            {
                (doc.account, doc.bank_guarantee_amount, 0),
                (settings.bank_guarantee_receiving_insurance_account, 0, doc.bank_guarantee_amount),
            },
        )
