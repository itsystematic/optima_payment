# Copyright (c) 2024, IT Systematic and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log import (
    ChequeActionLog,
    add_cheque_action_log,
)


class TestChequeActionLog(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_validate_posting_date_rejects_earlier_log_entries(self):
        log = ChequeActionLog(
            {
                "doctype": "Cheque Action Log",
                "name": "LOG-0002",
                "payment_entry": "PAY-0001",
                "posting_date": "2026-06-01",
            }
        )

        with patch(
            "optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log.frappe.db.get_all",
            return_value=[{"posting_date": "2026-06-02"}],
        ):
            with self.assertRaises(frappe.ValidationError) as exc:
                log.validate_posting_date()

        self.assertIn("Posting Date should not be earlier than 2026-06-02", str(exc.exception))

    def test_add_cheque_action_log_skips_cancelled_payment_entries(self):
        payment_entry = SimpleNamespace(
            docstatus=2,
            company="Test Company",
            name="PAY-0001",
            db_set=Mock(),
        )

        with patch(
            "optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log.frappe.get_doc"
        ) as get_doc_mock:
            add_cheque_action_log(payment_entry, "Collected")

        get_doc_mock.assert_not_called()
        payment_entry.db_set.assert_not_called()

    def test_add_cheque_action_log_creates_log_and_updates_payment_entry_status(self):
        payment_entry = SimpleNamespace(
            docstatus=1,
            company="Test Company",
            name="PAY-0001",
            db_set=Mock(),
        )
        cheque_log = SimpleNamespace(flags=SimpleNamespace(), save=Mock())

        with patch(
            "optima_payment.optima_payment.doctype.cheque_action_log.cheque_action_log.frappe.get_doc",
            return_value=cheque_log,
        ) as get_doc_mock:
            add_cheque_action_log(
                payment_entry,
                "Rejected",
                mode_of_payment="Bank Transfer",
                bank_fees_amount=25.5,
                posting_date="2026-06-03",
                cost_center="Main - TC",
            )

        get_doc_mock.assert_called_once_with(
            {
                "doctype": "Cheque Action Log",
                "company": "Test Company",
                "payment_entry": "PAY-0001",
                "cheque_status": "Rejected",
                "mode_of_payment": "Bank Transfer",
                "bank_fees_amount": 25.5,
                "posting_date": "2026-06-03",
                "cost_center": "Main - TC",
            }
        )
        self.assertTrue(cheque_log.flags.ignore_permissions)
        self.assertTrue(cheque_log.flags.ignore_mandatory)
        cheque_log.save.assert_called_once_with()
        payment_entry.db_set.assert_called_once_with({"cheque_status": "Rejected"})
