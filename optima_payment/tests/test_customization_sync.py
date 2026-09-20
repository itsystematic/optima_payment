"""Tests for the ownership-aware customization sync and the one-time adoption patch.

No test runs a real custom field create or update: Frappe alters the table and commits, which the
per-test rollback cannot undo. Custom Field rows are written with ``db_insert`` instead, and custom
field syncing is checked through its dry-run plan.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

import optima_payment.setup.sync as customization_sync
from optima_payment.setup import form_snapshot
from optima_payment.patches import adopt_existing_customizations as adoption_patch
from optima_payment.setup.sync import custom_fields, property_setters, remove_customizations
from optima_payment.setup.sync.declarations import (
    DeclarationConflict,
    _merge_declarations,
    get_declared_custom_fields,
    get_declared_property_setters,
)

TEST_DOCTYPE = "Note"
TEST_FIELD = {"fieldname": "optima_test_field", "label": "Optima Test", "fieldtype": "Data", "insert_after": "title"}
LAYOUT_BREAKS = ("Section Break", "Column Break", "Tab Break")


def make_setter(fieldname, property_name, value, property_type="Data", doctype=TEST_DOCTYPE):
    """Build a property setter declaration in the normalized shape the sync functions receive."""
    return {
        "doctype": doctype,
        "doctype_or_field": "DocField" if fieldname else "DocType",
        "fieldname": fieldname,
        "row_name": None,
        "property": property_name,
        "value": value,
        "property_type": property_type,
    }


def insert_setter(setter, value=None, is_system_generated=True):
    frappe.make_property_setter(
        {**setter, "value": setter["value"] if value is None else value},
        validate_fields_for_doctype=False,
        is_system_generated=is_system_generated,
    )


def delete_setters(setter):
    for row in property_setters.get_rows(setter):
        frappe.db.delete("Property Setter", row.name)


def get_setter_row(setter):
    rows = property_setters.get_rows(setter)
    return rows[0] if rows else None


def insert_custom_field_row(doctype, is_system_generated, **values):
    """Write a Custom Field row without the column change, and commit, that a normal insert triggers."""
    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "name": f"{doctype}-{values['fieldname']}",
            "dt": doctype,
            "is_system_generated": is_system_generated,
            **values,
        }
    ).db_insert()


class CustomizationTestCase(FrappeTestCase):
    def setUp(self):
        frappe.db.delete("Property Setter", {"doc_type": TEST_DOCTYPE})
        frappe.db.delete("Custom Field", {"dt": TEST_DOCTYPE})

    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache()


class TestPropertySetterSync(CustomizationTestCase):
    def test_creates_a_missing_setter_as_app_owned(self):
        setter = make_setter("title", "bold", "1", "Check")

        changes = property_setters.sync([setter], dry_run=False)

        self.assertEqual([change.action for change in changes], ["create"])
        row = get_setter_row(setter)
        self.assertEqual((row.value, row.is_system_generated), ("1", 1))

    def test_updates_an_app_owned_setter_that_drifted_from_code(self):
        setter = make_setter("title", "bold", "1", "Check")
        insert_setter(setter, value="0")

        changes = property_setters.sync([setter], dry_run=False)

        self.assertEqual([change.action for change in changes], ["update"])
        self.assertEqual(get_setter_row(setter).value, "1")

    def test_keeps_the_client_value(self):
        setter = make_setter("title", "bold", "1", "Check")
        insert_setter(setter, value="0", is_system_generated=False)

        changes = property_setters.sync([setter], dry_run=False)

        self.assertEqual([change.action for change in changes], ["keep"])
        row = get_setter_row(setter)
        self.assertEqual((row.value, row.is_system_generated), ("0", 0))

    def test_dry_run_writes_nothing(self):
        setter = make_setter("title", "bold", "1", "Check")

        changes = property_setters.sync([setter], dry_run=True)

        self.assertEqual([change.action for change in changes], ["create"])
        self.assertIsNone(get_setter_row(setter))

    def test_never_syncs_field_order(self):
        field_order = make_setter(None, "field_order", json.dumps(["title", "content"]))
        insert_setter(field_order, value=json.dumps(["content", "title"]))

        changes = property_setters.sync([field_order], dry_run=False)

        self.assertEqual(changes, [])
        self.assertEqual(get_setter_row(field_order).value, json.dumps(["content", "title"]))


class TestStartingFieldOrders(CustomizationTestCase):
    def test_writes_the_declared_field_order_where_the_doctype_has_none(self):
        field_order = make_setter(None, "field_order", json.dumps(["content", "title"]))

        changes = property_setters.create_missing_field_orders([field_order], dry_run=False)

        self.assertEqual([change.action for change in changes], ["create"])
        row = get_setter_row(field_order)
        self.assertEqual((row.value, row.is_system_generated), (json.dumps(["content", "title"]), 1))

    def test_leaves_an_existing_field_order_alone(self):
        field_order = make_setter(None, "field_order", json.dumps(["content", "title"]))
        insert_setter(field_order, value=json.dumps(["title", "content"]), is_system_generated=False)

        changes = property_setters.create_missing_field_orders([field_order], dry_run=False)

        self.assertEqual([change.action for change in changes], ["keep"])
        row = get_setter_row(field_order)
        self.assertEqual((row.value, row.is_system_generated), (json.dumps(["title", "content"]), 0))


class TestCustomFieldPlan(CustomizationTestCase):
    def plan(self):
        return custom_fields.sync({TEST_DOCTYPE: [TEST_FIELD]}, dry_run=True)

    def test_plans_a_missing_field_as_create_without_writing(self):
        self.assertEqual([change.action for change in self.plan()], ["create"])
        self.assertFalse(frappe.db.exists("Custom Field", {"dt": TEST_DOCTYPE, "fieldname": TEST_FIELD["fieldname"]}))

    def test_needs_no_change_when_the_field_matches_code(self):
        insert_custom_field_row(TEST_DOCTYPE, 1, **TEST_FIELD)

        self.assertEqual(self.plan(), [])

    def test_plans_an_update_for_an_app_owned_field_that_drifted(self):
        insert_custom_field_row(TEST_DOCTYPE, 1, **{**TEST_FIELD, "label": "Old Label"})

        [change] = self.plan()

        self.assertEqual(change.action, "update")
        self.assertIn("label", change.detail)

    def test_keeps_a_field_at_flag_0(self):
        insert_custom_field_row(TEST_DOCTYPE, 0, **{**TEST_FIELD, "label": "Client Label"})

        [change] = self.plan()

        self.assertEqual(change.action, "keep")

    def test_reports_a_fieldtype_change_as_conflict(self):
        insert_custom_field_row(TEST_DOCTYPE, 1, **{**TEST_FIELD, "fieldtype": "Int"})

        [change] = self.plan()

        self.assertEqual(change.action, "conflict")


class TestRemoval(CustomizationTestCase):
    def test_removes_app_owned_setters_and_keeps_client_values(self):
        app_owned = make_setter("title", "bold", "1", "Check")
        imported = make_setter("title", "in_global_search", "1", "Check")
        client_owned = make_setter("content", "bold", "1", "Check")
        insert_setter(app_owned)
        insert_setter(imported, is_system_generated=False)
        insert_setter(client_owned, value="0", is_system_generated=False)

        property_setters.remove([app_owned, imported, client_owned], {}, dry_run=False)

        self.assertIsNone(get_setter_row(app_owned))
        self.assertIsNone(get_setter_row(imported))
        kept = get_setter_row(client_owned)
        self.assertIsNotNone(kept, "the client's own value was deleted")
        self.assertEqual(kept.value, "0")

    def test_removing_a_declared_field_removes_every_setter_on_it(self):
        insert_custom_field_row(TEST_DOCTYPE, 1, **TEST_FIELD)
        on_field = make_setter(TEST_FIELD["fieldname"], "bold", "1", "Check")
        insert_setter(on_field, value="0", is_system_generated=False)
        declared_fields = {TEST_DOCTYPE: [TEST_FIELD]}

        self.assertEqual(property_setters.remove([on_field], declared_fields, dry_run=False), [])
        self.assertIsNotNone(get_setter_row(on_field))

        custom_fields.remove(declared_fields, dry_run=False)

        self.assertFalse(frappe.db.exists("Custom Field", f"{TEST_DOCTYPE}-{TEST_FIELD['fieldname']}"))
        self.assertIsNone(get_setter_row(on_field))


class TestDeclarations(FrappeTestCase):
    def test_enabled_features_declare_without_conflicts(self):
        self.assertTrue(get_declared_custom_fields())
        self.assertTrue(get_declared_property_setters())

    def test_repeated_declarations_merge_when_they_agree(self):
        merged = _merge_declarations({"fieldname": "x", "label": "X"}, {"fieldname": "x", "hidden": 1}, "Note.x")

        self.assertEqual(merged, {"fieldname": "x", "label": "X", "hidden": 1})

    def test_repeated_declarations_that_disagree_raise(self):
        with self.assertRaises(DeclarationConflict):
            _merge_declarations({"label": "X"}, {"label": "Y"}, "Note.x")


class TestAdoptExistingCustomizations(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache()

    def get_installed_field(self):
        """Return a declared field whose row on this site matches its declaration."""
        for doctype, fields in get_declared_custom_fields().items():
            rows = custom_fields.get_rows({doctype: fields})
            for field in fields:
                row = rows.get((doctype, field["fieldname"]))
                if row and field.get("label") and field["fieldtype"] not in LAYOUT_BREAKS and not custom_fields.get_differences(row, field):
                    return doctype, field, row.name
        self.skipTest("no declared custom field on this site matches its declaration")

    def get_declared_setters(self, count):
        setters = [
            setter
            for setter in get_declared_property_setters()
            if setter["property"] != "field_order" and frappe.db.exists("DocType", setter["doctype"])
        ]
        if len(setters) < count:
            self.skipTest(f"fewer than {count} declared property setters apply to this site")
        return setters[:count]

    def test_adopting_a_field_keeps_the_site_value_and_the_form(self):
        doctype, field, name = self.get_installed_field()
        label_setter = make_setter(field["fieldname"], "label", "", doctype=doctype)
        delete_setters(label_setter)
        frappe.db.set_value("Custom Field", name, {"is_system_generated": 0, "label": "Site Label"})
        frappe.clear_cache(doctype=doctype)

        adoption_patch.adopt_custom_fields()

        row = frappe.db.get_value("Custom Field", name, ["is_system_generated", "label"], as_dict=True)
        self.assertEqual((row.is_system_generated, row.label), (1, field["label"]))
        kept = get_setter_row(label_setter)
        self.assertEqual((kept.value, kept.is_system_generated), ("Site Label", 0))
        self.assertEqual(frappe.get_meta(doctype, cached=False).get_field(field["fieldname"]).label, "Site Label")

    def test_a_fieldtype_change_is_left_at_flag_0(self):
        doctype, field, name = self.get_installed_field()
        other_fieldtype = "Small Text" if field["fieldtype"] != "Small Text" else "Data"
        frappe.db.set_value("Custom Field", name, {"is_system_generated": 0, "fieldtype": other_fieldtype})

        changes = adoption_patch.adopt_custom_fields()

        [change] = [change for change in changes if change.target == f"{doctype}.{field['fieldname']}"]
        self.assertEqual(change.action, "conflict")
        self.assertEqual(frappe.db.get_value("Custom Field", name, "is_system_generated"), 0)

    def test_adopts_only_setters_that_hold_the_code_value(self):
        code_value, client_value = self.get_declared_setters(2)
        for setter in (code_value, client_value):
            delete_setters(setter)
        insert_setter(code_value, is_system_generated=False)
        insert_setter(client_value, value=f"{client_value['value']}-client", is_system_generated=False)

        adoption_patch.adopt_property_setters()

        self.assertEqual(get_setter_row(code_value).is_system_generated, 1)
        self.assertEqual(get_setter_row(client_value).is_system_generated, 0)

    def test_field_order_is_never_adopted(self):
        field_orders = [
            setter
            for setter in get_declared_property_setters()
            if setter["property"] == "field_order" and frappe.db.exists("DocType", setter["doctype"])
        ]
        if not field_orders:
            self.skipTest("no declared field_order applies to this site")
        delete_setters(field_orders[0])
        insert_setter(field_orders[0], is_system_generated=False)

        adoption_patch.adopt_property_setters()

        self.assertEqual(get_setter_row(field_orders[0]).is_system_generated, 0)


class TestClientCustomizationsAreNeverTouched(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache()

    def test_client_records_survive_adoption_sync_and_uninstall(self):
        doctype = next(doctype for doctype in get_declared_custom_fields() if frappe.db.exists("DocType", doctype))
        declared_setter_keys = {
            (setter["doctype"], setter["fieldname"], setter["property"]) for setter in get_declared_property_setters()
        }
        standard_field = next(
            df.fieldname
            for df in frappe.get_meta(doctype).fields
            if not df.get("is_custom_field") and (doctype, df.fieldname, "bold") not in declared_setter_keys
        )
        insert_custom_field_row(
            doctype, 0, fieldname="custom_client_note", label="Client Note", fieldtype="Data", insert_after=standard_field
        )
        client_setter = make_setter(standard_field, "bold", "1", "Check", doctype=doctype)
        delete_setters(client_setter)
        insert_setter(client_setter, is_system_generated=False)
        field_before = frappe.db.get_value("Custom Field", f"{doctype}-custom_client_note", "*", as_dict=True)
        setter_before = frappe.db.get_value("Property Setter", get_setter_row(client_setter).name, "*", as_dict=True)

        adoption_patch.adopt_custom_fields()
        adoption_patch.adopt_property_setters()
        property_setters.sync(get_declared_property_setters(), dry_run=False)
        remove_customizations()

        self.assertEqual(frappe.db.get_value("Custom Field", field_before.name, "*", as_dict=True), field_before)
        self.assertEqual(frappe.db.get_value("Property Setter", setter_before.name, "*", as_dict=True), setter_before)

    def test_the_sync_package_offers_no_adoption(self):
        self.assertEqual([name for name in dir(customization_sync) if "adopt" in name], [])


class TestFormSnapshot(CustomizationTestCase):
    def test_reports_nothing_when_the_forms_are_unchanged(self):
        before = form_snapshot.snapshot([TEST_DOCTYPE])

        self.assertEqual(form_snapshot.compare(before, form_snapshot.snapshot([TEST_DOCTYPE])), [])

    def test_reports_a_changed_property(self):
        before = form_snapshot.snapshot([TEST_DOCTYPE])
        insert_setter(make_setter("title", "bold", "1", "Check"))

        [difference] = form_snapshot.compare(before, form_snapshot.snapshot([TEST_DOCTYPE]))

        self.assertIn(f"{TEST_DOCTYPE}.title.bold", difference)

    def test_reports_a_changed_field_order(self):
        before = form_snapshot.snapshot([TEST_DOCTYPE])
        order = before["doctypes"][TEST_DOCTYPE]["order"]
        insert_setter(make_setter(None, "field_order", json.dumps(list(reversed(order)))))

        differences = form_snapshot.compare(before, form_snapshot.snapshot([TEST_DOCTYPE]))

        self.assertIn(f"{TEST_DOCTYPE}: field order changed", differences)

    def test_reports_a_field_that_disappeared(self):
        insert_custom_field_row(TEST_DOCTYPE, 1, **TEST_FIELD)
        frappe.clear_cache(doctype=TEST_DOCTYPE)
        before = form_snapshot.snapshot([TEST_DOCTYPE])
        custom_fields.remove({TEST_DOCTYPE: [TEST_FIELD]}, dry_run=False)

        differences = form_snapshot.compare(before, form_snapshot.snapshot([TEST_DOCTYPE]))

        self.assertIn(f"{TEST_DOCTYPE}.{TEST_FIELD['fieldname']}: field gone", differences)
