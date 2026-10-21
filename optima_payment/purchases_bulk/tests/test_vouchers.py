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
    BULK_ACTIONS,
    CANCEL,
    CANCELLED,
    DELETE,
    DELETED,
    DRAFT,
    SUBMIT,
    SUBMITTED,
    GroupKey,
    _bulk_failure_message,
    _bulk_order,
    _bulk_step,
    _failure_message,
    _group_rows,
    _nothing_to_do_message,
    _rollback_action,
    _row_amount,
    _row_values,
    _rows_by_voucher,
    _voucher_fields,
    _voucher_status,
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

    def test_the_tool_warehouse_goes_on_the_header_and_makes_an_invoice_update_stock(self):
        cases = [
            ("Purchase Order", WAREHOUSE, (WAREHOUSE, None)),
            ("Purchase Receipt", WAREHOUSE, (WAREHOUSE, None)),
            ("Purchase Invoice", WAREHOUSE, (WAREHOUSE, 1)),
            ("Purchase Invoice", None, (None, 0)),
        ]
        for voucher_type, set_warehouse, expected in cases:
            with self.subTest(voucher_type=voucher_type, set_warehouse=set_warehouse):
                fields = _voucher_fields(voucher_type, COMPANY, set_warehouse, key(), [row()])
                self.assertEqual((fields.get("set_warehouse"), fields.get("update_stock")), expected)

    def test_each_line_carries_its_row_qty(self):
        fields = _voucher_fields("Purchase Invoice", COMPANY, None, key(), [row(1, qty=3), row(2, qty=0.5)])

        self.assertEqual([line["qty"] for line in fields["items"]], [3, 0.5])

    def test_a_row_warehouse_goes_on_its_line_only_when_the_tool_has_a_warehouse(self):
        line = {"item_code": "Cement", "qty": 1, "rate": 100}
        with_warehouse = {**line, "warehouse": OTHER_WAREHOUSE}
        cases = [
            ("Purchase Order", WAREHOUSE, OTHER_WAREHOUSE, with_warehouse),
            ("Purchase Receipt", WAREHOUSE, OTHER_WAREHOUSE, with_warehouse),
            ("Purchase Invoice", WAREHOUSE, OTHER_WAREHOUSE, with_warehouse),
            ("Purchase Invoice", None, OTHER_WAREHOUSE, line),
            ("Purchase Receipt", WAREHOUSE, None, line),
        ]
        for voucher_type, set_warehouse, warehouse, expected in cases:
            with self.subTest(voucher_type=voucher_type, set_warehouse=set_warehouse, warehouse=warehouse):
                fields = _voucher_fields(voucher_type, COMPANY, set_warehouse, key(), [row(warehouse=warehouse)])
                self.assertEqual(fields["items"], [expected])

    def test_a_row_warehouse_leaves_the_header_warehouse_in_place(self):
        fields = _voucher_fields("Purchase Receipt", COMPANY, WAREHOUSE, key(), [row(warehouse=OTHER_WAREHOUSE)])

        self.assertEqual(fields["set_warehouse"], WAREHOUSE)


class TestRowStatus(FrappeTestCase):
    def test_a_voucher_marks_its_rows_by_its_docstatus(self):
        cases = [(0, DRAFT), (1, SUBMITTED), (2, CANCELLED), (None, DELETED)]
        for docstatus, status in cases:
            with self.subTest(docstatus=docstatus):
                self.assertEqual(_voucher_status(docstatus), status)

    def test_only_a_deleted_row_drops_its_voucher_link(self):
        unlinked = {"reference_doctype": None, "reference_name": None}
        cases = [
            (DRAFT, {"status": DRAFT}),
            (SUBMITTED, {"status": SUBMITTED}),
            (CANCELLED, {"status": CANCELLED}),
            (DELETED, {"status": DELETED, **unlinked}),
        ]
        for status, values in cases:
            with self.subTest(status=status):
                self.assertEqual(_row_values(status), values)

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


class TestBulkStep(FrappeTestCase):
    def test_which_vouchers_each_action_takes_and_where_their_rows_end(self):
        cases = [
            (SUBMIT, 0, (True, SUBMITTED)),
            (SUBMIT, 1, (False, SUBMITTED)),
            (SUBMIT, 2, (False, CANCELLED)),
            (SUBMIT, None, (False, DELETED)),
            (CANCEL, 0, (False, DRAFT)),
            (CANCEL, 1, (True, CANCELLED)),
            (CANCEL, 2, (False, CANCELLED)),
            (CANCEL, None, (False, DELETED)),
            (DELETE, 0, (True, DELETED)),
            (DELETE, 1, (False, SUBMITTED)),
            (DELETE, 2, (True, DELETED)),
            (DELETE, None, (False, DELETED)),
        ]
        for action, docstatus, expected in cases:
            with self.subTest(action=action, docstatus=docstatus):
                self.assertEqual(_bulk_step(action, docstatus), expected)


class TestVoucherOrder(FrappeTestCase):
    def test_vouchers_come_in_creation_order_with_all_their_rows(self):
        vouchers = _rows_by_voucher([row(1, voucher="PINV-1"), row(2, voucher="PINV-2"), row(3, voucher="PINV-1")])

        self.assertEqual(
            [(name, [r.idx for r in rows]) for (_doctype, name), rows in vouchers],
            [("PINV-1", [1, 3]), ("PINV-2", [2])],
        )

    def test_the_last_created_voucher_is_undone_first_with_all_its_rows(self):
        vouchers = _vouchers_newest_first(
            [row(1, voucher="PINV-1"), row(2, voucher="PINV-2"), row(3, voucher="PINV-1")]
        )

        self.assertEqual(
            [(name, [r.idx for r in rows]) for (_doctype, name), rows in vouchers],
            [("PINV-2", [2]), ("PINV-1", [1, 3])],
        )

    def test_submit_all_goes_in_creation_order_and_cancel_or_delete_all_newest_first(self):
        rows = [row(1, voucher="PINV-1"), row(2, voucher="PINV-2")]
        cases = [(SUBMIT, ["PINV-1", "PINV-2"]), (CANCEL, ["PINV-2", "PINV-1"]), (DELETE, ["PINV-2", "PINV-1"])]
        for action, names in cases:
            with self.subTest(action=action):
                self.assertEqual([name for (_doctype, name), _rows in _bulk_order(action, rows)], names)

    def test_rows_without_a_voucher_are_skipped(self):
        self.assertEqual(_rows_by_voucher([row(1), row(2)]), [])
        self.assertEqual(_vouchers_newest_first([row(1), row(2)]), [])


class TestMessages(FrappeTestCase):
    def test_a_creation_failure_names_the_voucher_type_supplier_date_and_rows(self):
        message = _failure_message("Purchase Invoice", key(), [row(1), row(3)])

        for part in ("Purchase Invoice", SUPPLIER, formatdate(DATE), "(rows 1, 3)"):
            with self.subTest(part=part):
                self.assertIn(part, message)

    def test_a_bulk_failure_names_the_action_voucher_and_rows(self):
        for action in BULK_ACTIONS:
            message = _bulk_failure_message(action, "Purchase Invoice", "PINV-1", [row(1), row(3)])
            for part in (action, "Purchase Invoice", "PINV-1", "(rows 1, 3)", "No voucher was changed"):
                with self.subTest(action=action, part=part):
                    self.assertIn(part, message)

    def test_nothing_to_do_names_the_action(self):
        for action in BULK_ACTIONS:
            with self.subTest(action=action):
                self.assertIn(action, _nothing_to_do_message(action))
