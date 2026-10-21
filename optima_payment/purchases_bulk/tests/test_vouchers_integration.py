# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The Purchases Bulk Tool through real saves, submits and cancels.

The branch matrix is in test_vouchers.py. These prove what only a real voucher shows: the rows are
stamped, ERPNext keeps the typed qty, rate, row date and row warehouse, the template's taxes reach the
voucher, a failure leaves nothing behind, and a voucher can be cancelled or deleted while the tool
stays submitted, by hand or through the bulk actions. A deleted voucher's rows lose their link, so a
later voucher given the same name by the naming series stays out of the tool.
"""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from optima_payment.purchases_bulk import api, vouchers
from optima_payment.purchases_bulk.vouchers import CANCEL, DELETE, SUBMIT
from optima_payment.tests.utils import (
    get_or_create_purchase_item,
    get_or_create_supplier,
    get_or_create_warehouse,
    make_purchases_bulk_tool,
    set_test_cost_center_default,
)


class TestPurchasesBulkToolIntegration(FrappeTestCase):
    def setUp(self):
        set_test_cost_center_default(erpnext.get_default_company())
        self.supplier_a = get_or_create_supplier("Optima Bulk Supplier A")
        self.supplier_b = get_or_create_supplier("Optima Bulk Supplier B")
        self.past_date = add_days(nowdate(), -3)

    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache(user=frappe.session.user)

    def get_vouchers(self, tool) -> list:
        names = dict.fromkeys(row.reference_name for row in tool.items)
        return [frappe.get_doc(tool.voucher_type, name) for name in names]

    def get_voucher_names(self, tool) -> list:
        return [row.reference_name for row in tool.items]

    def get_docstatuses(self, voucher_type, names) -> list:
        """Each voucher's docstatus, None once it is deleted."""
        return [frappe.db.get_value(voucher_type, name, "docstatus") for name in names]

    def get_statuses(self, tool) -> list:
        tool.reload()
        return [row.status for row in tool.items]

    def get_links(self, tool) -> list:
        tool.reload()
        return self.get_voucher_names(tool)

    def set_delete_linked_ledger_entries(self, value: int):
        """Whether deleting a cancelled invoice also deletes its ledger rows, which otherwise block it.

        The setting is cached outside the transaction, so its cache is cleared after the rollback.
        """
        frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", value)
        self.addCleanup(frappe.clear_document_cache, "Accounts Settings", "Accounts Settings")

    def make_mixed_tool(self):
        """A tool of two vouchers: supplier A's submitted, supplier B's still a draft."""
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        self.get_vouchers(tool)[0].submit()
        vouchers.sync_statuses(tool)
        return tool

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

    def test_row_qty_reaches_the_line_and_the_amount(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a, "qty": 3, "rate": 100}])

        row = tool.items[0]
        (voucher,) = self.get_vouchers(tool)
        self.assertEqual(voucher.items[0].qty, 3)
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

    def test_a_row_warehouse_wins_over_the_tool_warehouse(self):
        company = erpnext.get_default_company()
        tool_warehouse = get_or_create_warehouse(company, "Optima Bulk Tool Warehouse")
        row_warehouse = get_or_create_warehouse(company, "Optima Bulk Row Warehouse")
        stock_item = get_or_create_purchase_item(company, "Optima Test Purchase Stock Item", is_stock_item=1)
        tool = make_purchases_bulk_tool(
            voucher_type="Purchase Receipt",
            set_warehouse=tool_warehouse,
            rows=[
                {"supplier": self.supplier_a, "item": stock_item, "warehouse": row_warehouse},
                {"supplier": self.supplier_a, "item": stock_item},
            ],
        )

        (receipt,) = self.get_vouchers(tool)
        self.assertEqual([line.warehouse for line in receipt.items], [row_warehouse, tool_warehouse])

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
        self.assertEqual(self.get_links(tool), [None, None])

    def test_cancelling_the_tool_after_cancel_all_keeps_every_row_cancelled(self):
        tool = make_purchases_bulk_tool(
            rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}], auto_submit=1
        )
        vouchers.run_bulk_action(tool, CANCEL)

        tool.reload()
        tool.cancel()

        self.assertEqual(self.get_statuses(tool), ["Cancelled", "Cancelled"])

    # ============================================================================================
    # BULK ACTIONS

    def test_a_voucher_can_be_cancelled_or_deleted_on_its_own(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        submitted, draft = self.get_vouchers(tool)
        submitted.submit()

        submitted.cancel()
        frappe.delete_doc(draft.doctype, draft.name)
        vouchers.sync_statuses(tool)

        self.assertEqual(self.get_statuses(tool), ["Cancelled", "Deleted"])

    def test_deleting_a_voucher_by_hand_unlinks_its_rows_at_once(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        kept, deleted = self.get_vouchers(tool)

        frappe.delete_doc(deleted.doctype, deleted.name)

        self.assertEqual(self.get_links(tool), [kept.name, None])
        self.assertEqual(self.get_statuses(tool), ["Draft", "Deleted"])

    def test_a_voucher_given_a_deleted_name_stays_out_of_the_tool(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}])
        names = self.get_voucher_names(tool)
        api.run_bulk_action(tool.name, DELETE)

        other = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_b}])
        self.assertEqual(self.get_voucher_names(other), names, "the naming series should give the name out again")

        api.update_statuses(tool.name)
        api.run_bulk_action(tool.name, SUBMIT)
        tool.reload()
        tool.cancel()

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [0])
        self.assertEqual(self.get_statuses(tool), ["Deleted"])
        self.assertEqual(self.get_links(tool), [None])

    def test_update_status_shows_a_draft_submitted_on_its_own(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}])
        (voucher,) = self.get_vouchers(tool)

        voucher.submit()
        api.update_statuses(tool.name)

        self.assertEqual(self.get_statuses(tool), ["Submitted"])

    def test_submit_all_submits_the_drafts_and_the_tool_stays_submitted(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        names = self.get_voucher_names(tool)

        api.run_bulk_action(tool.name, SUBMIT)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [1, 1])
        self.assertEqual(self.get_statuses(tool), ["Submitted", "Submitted"])
        self.assertEqual(tool.docstatus, 1)

    def test_cancel_all_leaves_the_drafts(self):
        tool = self.make_mixed_tool()
        names = self.get_voucher_names(tool)

        vouchers.run_bulk_action(tool, CANCEL)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [2, 0])
        self.assertEqual(self.get_statuses(tool), ["Cancelled", "Draft"])

    def test_delete_all_leaves_the_submitted_vouchers(self):
        tool = self.make_mixed_tool()
        names = self.get_voucher_names(tool)

        vouchers.run_bulk_action(tool, DELETE)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [1, None])
        self.assertEqual(self.get_statuses(tool), ["Submitted", "Deleted"])
        self.assertEqual(self.get_links(tool), [names[0], None])

    def test_delete_all_deletes_cancelled_vouchers_too(self):
        tool = self.make_mixed_tool()
        names = self.get_voucher_names(tool)
        self.get_vouchers(tool)[0].cancel()
        self.set_delete_linked_ledger_entries(1)

        vouchers.run_bulk_action(tool, DELETE)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [None, None])
        self.assertEqual(self.get_statuses(tool), ["Deleted", "Deleted"])

    def test_delete_all_deletes_nothing_when_a_cancelled_invoice_keeps_its_ledger_rows(self):
        tool = self.make_mixed_tool()
        names = self.get_voucher_names(tool)
        self.get_vouchers(tool)[0].cancel()
        self.set_delete_linked_ledger_entries(0)

        with self.assertRaises(frappe.ValidationError):
            vouchers.run_bulk_action(tool, DELETE)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [2, 0])
        self.assertEqual(self.get_links(tool), names)

    def test_submit_all_submits_nothing_when_one_voucher_fails(self):
        tool = make_purchases_bulk_tool(rows=[{"supplier": self.supplier_a}, {"supplier": self.supplier_b}])
        names = self.get_voucher_names(tool)
        frappe.db.set_value("Supplier", self.supplier_b, "disabled", 1)

        with self.assertRaises(frappe.ValidationError):
            vouchers.run_bulk_action(tool, SUBMIT)

        self.assertEqual(self.get_docstatuses(tool.voucher_type, names), [0, 0])
        self.assertEqual(self.get_statuses(tool), ["Draft", "Draft"])

    def test_the_api_refuses_a_draft_tool_and_an_unknown_action(self):
        draft_tool = make_purchases_bulk_tool(do_not_submit=True)
        submitted_tool = make_purchases_bulk_tool()
        cases = [
            ("update status on a draft tool", lambda: api.update_statuses(draft_tool.name)),
            ("bulk action on a draft tool", lambda: api.run_bulk_action(draft_tool.name, SUBMIT)),
            ("unknown action", lambda: api.run_bulk_action(submitted_tool.name, "amend")),
        ]
        for label, call in cases:
            with self.subTest(case=label), self.assertRaises(frappe.ValidationError):
                call()
