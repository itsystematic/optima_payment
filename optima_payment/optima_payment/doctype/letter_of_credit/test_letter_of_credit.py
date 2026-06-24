# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""Phase-1 integration tests for Letter of Credit.

GL/Payment Entry integration is deferred to a later phase, so these tests only
cover validation and status-only lifecycle transitions (submit, return, extend,
loss) - no GL Entry assertions, unlike Bank Guarantee-BG's test suite.
"""

import frappe
from frappe.utils import add_days, nowdate
from frappe.tests.utils import FrappeTestCase

from optima_payment.tests.utils import make_letter_of_credit


class TestLetterofCredit(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

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

    # ============================================================================================
    # SUBMIT / STATUS
    # ============================================================================================

    def test_submit_providing_sets_status_issued(self):
        doc = make_letter_of_credit(lc_type="Providing")
        self.assertEqual(doc.lc_status, "Issued")

    def test_submit_receiving_sets_status_exists(self):
        doc = make_letter_of_credit(lc_type="Receiving")
        self.assertEqual(doc.lc_status, "Exists")

    # ============================================================================================
    # RETURN
    # ============================================================================================

    def test_lc_return_sets_status_and_returned_date(self):
        doc = make_letter_of_credit(lc_type="Providing")

        doc.lc_return(nowdate())
        doc.reload()

        self.assertEqual(doc.lc_status, "Returned")
        self.assertEqual(doc.returned_date, frappe.utils.getdate(nowdate()))

    def test_lc_return_rejects_date_before_posting_date(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_return(add_days(nowdate(), -5))

    # ============================================================================================
    # EXTEND
    # ============================================================================================

    def test_lc_extend_action_updates_status_and_validity_fields(self):
        doc = make_letter_of_credit(lc_type="Providing")
        extend_to_date = add_days(doc.end_date, 1)

        doc.lc_extend_action(
            amount=20,
            end_date=add_days(doc.end_date, 9),
            days=10,
            extend_to_date=extend_to_date,
            has_commission=True,
        )
        doc.reload()

        self.assertEqual(doc.lc_status, "Extended")
        self.assertEqual(doc.no_of_extended_days, 10)
        self.assertEqual(doc.extend_validity, 1)

    def test_lc_extend_action_rejects_date_before_posting_date(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_extend_action(
                amount=0,
                end_date=doc.end_date,
                days=10,
                extend_to_date=add_days(nowdate(), -5),
                has_commission=False,
            )

    # ============================================================================================
    # LOSS
    # ============================================================================================

    def test_lc_loss_action_sets_status_lost(self):
        doc = make_letter_of_credit(lc_type="Providing")

        doc.lc_loss_action(nowdate())
        doc.reload()

        self.assertEqual(doc.lc_status, "Lost")

    def test_lc_loss_action_rejects_date_before_posting_date(self):
        doc = make_letter_of_credit(lc_type="Providing")

        with self.assertRaises(frappe.ValidationError):
            doc.lc_loss_action(add_days(nowdate(), -5))
