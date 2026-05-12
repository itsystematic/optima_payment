"""Frappe tests for the custom Payment Entry override."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.tests.utils import make_payment_entry
from optima_payment.override.doctype_class.payment_entry import CustomPaymentEntry


class TestCustomPaymentEntry(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_new_payment_entry_uses_custom_override(self):
        self.assertIsInstance(frappe.new_doc("Payment Entry"), CustomPaymentEntry)

    def test_multi_expense_pay_skips_party_side_account_mandatory_fields(self):
        pe = make_payment_entry(multi_expense=1)
        pe.set_missing_values()

        missing = {field for field, _message in pe._get_missing_mandatory_fields()}

        self.assertNotIn("paid_to", missing)
        self.assertNotIn("paid_to_account_currency", missing)
        self.assertEqual(pe.paid_to_account_currency, pe.paid_from_account_currency)

    def test_normal_pay_still_requires_party_side_account_fields(self):
        pe = make_payment_entry(multi_expense=0)

        missing = {field for field, _message in pe._get_missing_mandatory_fields()}

        self.assertIn("paid_to", missing)
        self.assertIn("paid_to_account_currency", missing)

    def test_multi_expense_validate_mandatory_keeps_exchange_rate_checks(self):
        pe = make_payment_entry(multi_expense=1)
        pe.target_exchange_rate = None

        pe.set_missing_values()

        with self.assertRaises(frappe.ValidationError) as exc:
            pe.validate_mandatory()

        self.assertIn("Target Exchange Rate", str(exc.exception))

    def test_on_submit_allows_difference_amount_for_multi_expense(self):
        pe = make_payment_entry(multi_expense=1)
        pe.difference_amount = 25

        with (
            patch.object(CustomPaymentEntry, "update_payment_requests", autospec=True) as update_requests,
            patch.object(CustomPaymentEntry, "update_payment_schedule", autospec=True) as update_schedule,
            patch.object(CustomPaymentEntry, "make_gl_entries", autospec=True) as make_gl_entries,
            patch.object(
                CustomPaymentEntry, "update_outstanding_amounts", autospec=True
            ) as update_outstanding,
            patch.object(CustomPaymentEntry, "set_status", autospec=True) as set_status,
        ):
            pe.on_submit()

        update_requests.assert_called_once_with(pe)
        update_schedule.assert_called_once_with(pe)
        make_gl_entries.assert_called_once_with(pe)
        update_outstanding.assert_called_once_with(pe)
        set_status.assert_called_once_with(pe)

    def test_on_submit_keeps_difference_amount_check_for_normal_entries(self):
        pe = make_payment_entry(multi_expense=0)
        pe.difference_amount = 25

        with self.assertRaises(frappe.ValidationError) as exc:
            pe.on_submit()

        self.assertIn("Difference Amount must be zero", str(exc.exception))
