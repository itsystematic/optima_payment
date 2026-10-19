# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The Purchases Bulk Tool through real saves, submits and cancels.

The branch matrix is in test_vouchers.py. These prove what only a real voucher shows: the rows are
stamped, ERPNext keeps the typed rate and the row date, the template's taxes reach the voucher, a
failure leaves nothing behind, and cancelling the tool gets past each voucher's back-link check.
"""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from optima_payment.purchases_bulk import api
from optima_payment.tests.utils import (
    get_or_create_purchase_item,
    get_or_create_supplier,
    make_purchases_bulk_tool,
)


class TestPurchasesBulkToolIntegration(FrappeTestCase):
    def setUp(self):
        self.supplier_a = get_or_create_supplier("Optima Bulk Supplier A")
        self.supplier_b = get_or_create_supplier("Optima Bulk Supplier B")
        self.past_date = add_days(nowdate(), -3)

    def tearDown(self):
        frappe.db.rollback()

    def get_vouchers(self, tool) -> list:
        names = dict.fromkeys(row.reference_name for row in tool.items)
        return [frappe.get_doc(tool.voucher_type, name) for name in names]

    # ============================================================================================
    # VOUCHER CREATION

    def test_rows_become_vouchers_with_their_rates_and_taxes(self):
        tool = make_purchases_bulk_tool(
            rows=[
                {"supplier": self.supplier_a, "rate": 100},
                {"supplier": self.supplier_b, "rate": 200},
                {"supplier": self.supplier_a, "rate": 300},
            ]
        )

        first, second, third = tool.items
        self.assertEqual(first.reference_name, third.reference_name)
        self.assertNotEqual(first.reference_name, second.reference_name)

        voucher_a, voucher_b = self.get_vouchers(tool)
        self.assertEqual([row.rate for row in voucher_a.items], [100, 300])
        self.assertEqual([row.rate for row in voucher_b.items], [200])
        for voucher in (voucher_a, voucher_b):
            self.assertEqual(voucher.taxes_and_charges, first.vat)
            self.assertTrue(voucher.taxes)

    def test_invoice_keeps_a_past_row_date(self):
        tool = make_purchases_bulk_tool(
            rows=[{"supplier": self.supplier_a, "voucher_posting_date": self.past_date}]
        )

        (invoice,) = self.get_vouchers(tool)
        self.assertEqual(getdate(invoice.posting_date), getdate(self.past_date))

    def test_auto_submit_submits_the_vouchers(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}], auto_submit=1)

        (voucher,) = self.get_vouchers(tool)
        self.assertEqual(voucher.docstatus, 1)
        self.assertEqual(tool.items[0].status, "Submitted")

    def test_without_auto_submit_vouchers_stay_draft(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}])

        (voucher,) = self.get_vouchers(tool)
        self.assertEqual(voucher.docstatus, 0)
        self.assertEqual(tool.items[0].status, "Draft")

    def test_row_amount_matches_the_voucher_total(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a, "rate": 100}])

        row = tool.items[0]
        template_rate = frappe.db.get_value(
            "Purchase Taxes and Charges", {"parent": row.vat, "charge_type": "On Net Total"}, "rate"
        )
        self.assertEqual(api.get_vat_rate(row.vat), template_rate)

        (voucher,) = self.get_vouchers(tool)
        self.assertEqual(voucher.grand_total, row.amount)

    def test_failed_voucher_creates_nothing(self):
        frappe.db.set_value("Supplier", self.supplier_b, "disabled", 1)
        invoices_before = frappe.db.count("Purchase Invoice", {"supplier": self.supplier_a})
        tool = make_purchases_bulk_tool(
            rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}],
            do_not_submit=True,
        )

        with self.assertRaises(frappe.ValidationError):
            tool.submit()

        self.assertEqual(frappe.db.count("Purchase Invoice", {"supplier": self.supplier_a}), invoices_before)

    # ============================================================================================
    # VOUCHER TYPES

    def test_purchase_order_uses_the_row_date(self):
        tool = make_purchases_bulk_tool(
            voucher_type="Purchase Order",
            rows=[{"supplier": self.supplier_a, "voucher_posting_date": self.past_date}],
        )

        (order,) = self.get_vouchers(tool)
        self.assertEqual(getdate(order.transaction_date), getdate(self.past_date))
        self.assertEqual(getdate(order.schedule_date), getdate(self.past_date))

    def test_purchase_receipt_uses_the_warehouse(self):
        company = erpnext.get_default_company()
        warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "disabled": 0})
        tool = make_purchases_bulk_tool(
            voucher_type="Purchase Receipt",
            set_warehouse=warehouse,
            rows=[
                {
                    "supplier": self.supplier_a,
                    "item": get_or_create_purchase_item(
                        company, "Optima Test Purchase Stock Item", is_stock_item=1
                    ),
                    "voucher_posting_date": self.past_date,
                }
            ],
        )

        (receipt,) = self.get_vouchers(tool)
        self.assertEqual(getdate(receipt.posting_date), getdate(self.past_date))
        self.assertEqual(receipt.items[0].warehouse, warehouse)

    # ============================================================================================
    # CANCEL

    def test_cancel_cancels_submitted_vouchers(self):
        tool = make_purchases_bulk_tool(
            rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}], auto_submit=1
        )
        voucher_names = [row.reference_name for row in tool.items]

        tool.cancel()
        tool.reload()

        for name in voucher_names:
            self.assertEqual(frappe.db.get_value("Purchase Invoice", name, "docstatus"), 2)
        self.assertEqual({row.status for row in tool.items}, {"Cancelled"})

    def test_cancel_deletes_draft_vouchers(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        voucher_names = [row.reference_name for row in tool.items]

        tool.cancel()
        tool.reload()

        for name in voucher_names:
            self.assertFalse(frappe.db.exists("Purchase Invoice", name))
        self.assertEqual({row.status for row in tool.items}, {"Deleted"})
