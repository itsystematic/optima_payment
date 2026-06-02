"""Focused tests for cheque GL currency handling."""

import unittest
from unittest.mock import patch

import frappe

from optima_payment.cheque import cases, utils


class _FakePaymentEntry:
    def __init__(self):
        self.company = "Test Company"
        self.company_currency = "SAR"
        self.cost_center = "Main - TC"
        self.project = None
        self.party = "Test Party"
        self.paid_from = "Source Account"
        self.paid_to = "Target Account"
        self.paid_from_account_currency = "USD"
        self.paid_to_account_currency = "USD"
        self.source_exchange_rate = 3.75
        self.target_exchange_rate = 3.75
        self.base_received_amount = 375

    def get(self, key, default=None):
        return getattr(self, key, default)

    def get_gl_dict(self, args, item=None):
        return frappe._dict(args)


class TestChequeGlCurrencyHandling(unittest.TestCase):
    @patch("optima_payment.cheque.utils.get_account_currency", return_value="USD")
    @patch("optima_payment.cheque.utils.get_exchange_rate")
    def test_create_gl_entry_uses_target_exchange_rate_for_account_currency(
        self, exchange_rate_mock, _account_currency_mock
    ):
        doc = _FakePaymentEntry()

        gl_entry = utils.create_gl_entry(
            doc,
            posting_date="2026-06-02",
            account="Cheque Wallet USD",
            debit=75,
            exchange_side="target",
        )

        self.assertEqual(gl_entry.debit_in_account_currency, 20)
        exchange_rate_mock.assert_not_called()

    @patch("optima_payment.cheque.utils.get_account_currency", return_value="EUR")
    @patch("optima_payment.cheque.utils.get_exchange_rate", return_value=5)
    def test_create_gl_entry_falls_back_to_account_exchange_rate(
        self, _exchange_rate_mock, _account_currency_mock
    ):
        doc = _FakePaymentEntry()

        gl_entry = utils.create_gl_entry(
            doc,
            posting_date="2026-06-02",
            account="Cheque Wallet EUR",
            debit=100,
            exchange_side="target",
        )

        self.assertEqual(gl_entry.debit_in_account_currency, 20)

    @patch("optima_payment.cheque.cases.finalize_gl_entries")
    @patch("optima_payment.cheque.cases.create_advance_gl")
    @patch("optima_payment.cheque.cases.create_party_gl")
    @patch("optima_payment.cheque.cases.create_gl_entry", side_effect=lambda *args, **kwargs: kwargs)
    @patch("optima_payment.cheque.cases.get_cheque_account", return_value="Incoming Wallet")
    def test_return_cheque_uses_target_side_base_amounts(
        self,
        _wallet_mock,
        create_gl_entry_mock,
        create_party_gl_mock,
        create_advance_gl_mock,
        finalize_gl_entries_mock,
    ):
        doc = _FakePaymentEntry()

        cases.make_return_cheque_gl.__closure__[0].cell_contents(
            doc, posting_date="2026-06-02", remarks="Returned"
        )

        manual_entries = [call.kwargs for call in create_gl_entry_mock.call_args_list]
        self.assertEqual(len(manual_entries), 3)
        self.assertEqual(
            [entry.get("debit", 0) or entry.get("credit", 0) for entry in manual_entries],
            [doc.base_received_amount, doc.base_received_amount, doc.base_received_amount],
        )
        self.assertTrue(all(entry["exchange_side"] == "target" for entry in manual_entries))
        create_party_gl_mock.assert_called_once()
        create_advance_gl_mock.assert_called_once()
        finalize_gl_entries_mock.assert_called_once()
