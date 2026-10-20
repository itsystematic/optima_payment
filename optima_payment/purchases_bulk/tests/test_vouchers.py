# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The branch matrix for the Purchases Bulk Tool. Nothing here writes to the database.

Rows are ``frappe._dict`` objects shaped like grid rows, so no supplier, item or tax template has to
exist on the site. The wiring through real saves is in test_vouchers_integration.py.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate, getdate

from optima_payment.purchases_bulk.vouchers import (
    CANCEL,
    CANCELLED,
    DELETE,
    DELETED,
    DRAFT,
    SUBMITTED,
    GroupKey,
    _created_status,
    _failure_message,
    _group_rows,
    _rollback_action,
    _row_amount,
    _voucher_fields,
    _vouchers_newest_first,
)

SUPPLIER = "Al Noor Trading"
OTHER_SUPPLIER = "Gulf Supplies"
VAT = "KSA VAT 15%"
OTHER_VAT = "Zero VAT"
DATE = "2026-10-12"
OTHER_DATE = "2026-10-13"
COMPANY = "Optima Test Company"
WAREHOUSE = "Stores"
OTHER_WAREHOUSE = "Yard"


def row(
    idx=1, *, supplier=SUPPLIER, date=DATE, vat=VAT, item="Cement", qty=1, rate=100, warehouse=None, voucher=None
):
    """A grid row the way the tool holds it. ``voucher`` names the Purchase Invoice it went into."""
    return frappe._dict(
        idx=idx,
        supplier=supplier,
        voucher_posting_date=date,
        vat=vat,
        item=item,
        qty=qty,
        rate=rate,
        warehouse=warehouse,
        reference_doctype="Purchase Invoice" if voucher else None,
        reference_name=voucher,
    )


def key(supplier=SUPPLIER, posting_date=DATE, vat=VAT):
    return GroupKey(supplier, getdate(posting_date), vat)


class TestRowAmount(FrappeTestCase):
    def test_vat_is_added_on_top_of_qty_times_rate(self):
        cases = [
            ("fifteen percent", 1, 100, 15, 115.0),
            ("zero rated", 1, 250, 0, 250.0),
            ("blank rate", 1, None, 15, 0.0),
            ("three units", 3, 100, 15, 345.0),
            ("zero qty", 0, 100, 15, 0.0),
            ("blank qty", None, 100, 15, 0.0),
        ]
        for label, qty, rate, vat_rate, amount in cases:
            with self.subTest(case=label):
                self.assertEqual(_row_amount(qty, rate, vat_rate, 2), amount)

    def test_the_amount_is_rounded_to_the_field_precision(self):
        self.assertEqual(_row_amount(1, 33.33, 15, 2), 38.33)


class TestGroupRows(FrappeTestCase):
    def test_rows_sharing_supplier_date_and_vat_share_a_voucher_in_first_seen_order(self):
        groups = _group_rows([row(1), row(2, supplier=OTHER_SUPPLIER), row(3)])

        self.assertEqual(
            [(group_key.supplier, [r.idx for r in rows]) for group_key, rows in groups.items()],
            [(SUPPLIER, [1, 3]), (OTHER_SUPPLIER, [2])],
        )

    def test_a_different_header_value_starts_a_new_voucher(self):
        cases = [
            ("supplier", {"supplier": OTHER_SUPPLIER}),
            ("date", {"date": OTHER_DATE}),
            ("vat", {"vat": OTHER_VAT}),
        ]
        for label, change in cases:
            with self.subTest(differs=label):
                self.assertEqual(len(_group_rows([row(1), row(2, **change)])), 2)

    def test_a_date_typed_as_text_or_as_a_date_is_one_voucher(self):
        groups = _group_rows([row(1, date=DATE), row(2, date=getdate(DATE))])

        self.assertEqual(list(groups), [key()])


class TestVoucherFields(FrappeTestCase):
    def test_the_header_comes_from_the_group_and_each_row_is_one_line_at_its_typed_rate(self):
        fields = _voucher_fields(
            "Purchase Invoice", COMPANY, None, key(), [row(1, rate=100), row(2, item="Sand", rate=300)]
        )

        self.assertEqual(
            (fields["company"], fields["supplier"], fields["taxes_and_charges"], fields["ignore_pricing_rule"]),
            (COMPANY, SUPPLIER, VAT, 1),
        )
        self.assertEqual(
            fields["items"],
            [{"item_code": "Cement", "qty": 1, "rate": 100}, {"item_code": "Sand", "qty": 1, "rate": 300}],
        )

    def test_each_voucher_type_gets_its_own_date_fields(self):
        posting_date = getdate(DATE)
        cases = [
            ("Purchase Order", {"transaction_date": posting_date, "schedule_date": posting_date}, "posting_date"),
            ("Purchase Invoice", {"set_posting_time": 1, "posting_date": posting_date}, "transaction_date"),
            ("Purchase Receipt", {"set_posting_time": 1, "posting_date": posting_date}, "transaction_date"),
        ]
        for voucher_type, dates, absent in cases:
            with self.subTest(voucher_type=voucher_type):
                fields = _voucher_fields(voucher_type, COMPANY, None, key(), [row()])
                self.assertEqual({fieldname: fields.get(fieldname) for fieldname in dates}, dates)
                self.assertNotIn(absent, fields)

    def test_the_warehouse_goes_only_on_orders_and_receipts(self):
        cases = [
            ("Purchase Order", WAREHOUSE, WAREHOUSE),
            ("Purchase Receipt", WAREHOUSE, WAREHOUSE),
            ("Purchase Invoice", WAREHOUSE, None),
            ("Purchase Receipt", None, None),
        ]
        for voucher_type, set_warehouse, expected in cases:
            with self.subTest(voucher_type=voucher_type, set_warehouse=set_warehouse):
                fields = _voucher_fields(voucher_type, COMPANY, set_warehouse, key(), [row()])
                self.assertEqual(fields.get("set_warehouse"), expected)

    def test_each_line_carries_its_row_qty(self):
        fields = _voucher_fields("Purchase Invoice", COMPANY, None, key(), [row(1, qty=3), row(2, qty=0.5)])

        self.assertEqual([line["qty"] for line in fields["items"]], [3, 0.5])

    def test_a_row_warehouse_goes_on_its_line_only_on_orders_and_receipts(self):
        line = {"item_code": "Cement", "qty": 1, "rate": 100}
        cases = [
            ("Purchase Order", OTHER_WAREHOUSE, {**line, "warehouse": OTHER_WAREHOUSE}),
            ("Purchase Receipt", OTHER_WAREHOUSE, {**line, "warehouse": OTHER_WAREHOUSE}),
            ("Purchase Invoice", OTHER_WAREHOUSE, line),
            ("Purchase Receipt", None, line),
        ]
        for voucher_type, warehouse, expected in cases:
            with self.subTest(voucher_type=voucher_type, warehouse=warehouse):
                fields = _voucher_fields(voucher_type, COMPANY, WAREHOUSE, key(), [row(warehouse=warehouse)])
                self.assertEqual(fields["items"], [expected])

    def test_a_row_warehouse_leaves_the_header_warehouse_in_place(self):
        fields = _voucher_fields("Purchase Receipt", COMPANY, WAREHOUSE, key(), [row(warehouse=OTHER_WAREHOUSE)])

        self.assertEqual(fields["set_warehouse"], WAREHOUSE)


class TestRowStatus(FrappeTestCase):
    def test_a_created_voucher_marks_its_rows_by_its_docstatus(self):
        self.assertEqual(_created_status(0), DRAFT)
        self.assertEqual(_created_status(1), SUBMITTED)

    def test_cancelling_the_tool_cancels_submitted_vouchers_and_deletes_drafts(self):
        cases = [
            ("submitted", 1, (CANCEL, CANCELLED)),
            ("draft", 0, (DELETE, DELETED)),
            ("already cancelled", 2, (None, CANCELLED)),
            ("no longer there", None, (None, DELETED)),
        ]
        for label, docstatus, expected in cases:
            with self.subTest(voucher=label):
                self.assertEqual(_rollback_action(docstatus), expected)


class TestVouchersNewestFirst(FrappeTestCase):
    def test_the_last_created_voucher_is_undone_first_with_all_its_rows(self):
        vouchers = _vouchers_newest_first(
            [row(1, voucher="PINV-1"), row(2, voucher="PINV-2"), row(3, voucher="PINV-1")]
        )

        self.assertEqual(
            [(name, [r.idx for r in rows]) for (_doctype, name), rows in vouchers],
            [("PINV-2", [2]), ("PINV-1", [1, 3])],
        )

    def test_rows_without_a_voucher_are_skipped(self):
        self.assertEqual(_vouchers_newest_first([row(1), row(2)]), [])


class TestFailureMessage(FrappeTestCase):
    def test_it_names_the_voucher_type_supplier_date_and_rows(self):
        message = _failure_message("Purchase Invoice", key(), [row(1), row(3)])

        for part in ("Purchase Invoice", SUPPLIER, formatdate(DATE), "(rows 1, 3)"):
            with self.subTest(part=part):
                self.assertIn(part, message)
