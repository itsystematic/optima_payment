"""Create, update and remove declared property setters, and write missing ``field_order``s."""

from __future__ import annotations

import frappe
from frappe.utils import cstr

from .declarations import property_setter_name
from .report import Change

FIELD_ORDER_PROPERTY = "field_order"


def sync(declared: list[dict], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    updated_doctypes: set[str] = set()

    for setter in declared:
        if setter["property"] == FIELD_ORDER_PROPERTY:
            continue

        name = property_setter_name(setter)
        if not frappe.db.exists("DocType", setter["doctype"]):
            changes.append(Change("missing", name, "doctype is not on this site"))
            continue

        rows = _get_rows(setter)
        change = _plan(name, setter, rows)
        if not change:
            continue
        changes.append(change)

        if dry_run:
            continue
        if change.action == "create":
            frappe.make_property_setter(setter, validate_fields_for_doctype=False, is_system_generated=True)
        elif change.action == "update":
            frappe.db.set_value(
                "Property Setter",
                rows[0].name,
                {"value": setter["value"], "property_type": setter["property_type"]},
            )
            updated_doctypes.add(setter["doctype"])

    for doctype in updated_doctypes:
        frappe.clear_cache(doctype=doctype)

    return changes


def create_missing_field_orders(declared: list[dict], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    for setter in declared:
        if setter["property"] != FIELD_ORDER_PROPERTY:
            continue

        name = property_setter_name(setter)
        if not frappe.db.exists("DocType", setter["doctype"]):
            changes.append(Change("missing", name, "doctype is not on this site"))
        elif _get_rows(setter):
            changes.append(Change("keep", name, "a field_order property setter already exists"))
        else:
            changes.append(Change("create", name))
            if not dry_run:
                frappe.make_property_setter(setter, validate_fields_for_doctype=False, is_system_generated=True)

    return changes


def remove(declared: list[dict], declared_fields: dict[str, list[dict]], dry_run: bool) -> list[Change]:
    """Delete declared property setters at flag 1, and at flag 0 when they still hold the declared value.

    Older imports wrote app setters with flag 0, so a flag-0 row with the declared value carries no
    client edit. Setters on the app's own custom fields are skipped because deleting the field
    removes them.
    """
    field_keys = {(doctype, field["fieldname"]) for doctype, fields in declared_fields.items() for field in fields}
    changes: list[Change] = []

    for setter in declared:
        if (setter["doctype"], setter["fieldname"]) in field_keys:
            continue

        for row in _get_rows(setter):
            if not row.is_system_generated and cstr(row.value) != cstr(setter["value"]):
                changes.append(Change("keep", row.name, "is_system_generated=0 with the client's own value"))
                continue

            detail = "" if row.is_system_generated else "is_system_generated=0 but holds the code value"
            changes.append(Change("remove", row.name, detail))
            if not dry_run:
                frappe.delete_doc("Property Setter", row.name, force=True)

    return changes


def _plan(name: str, setter: dict, rows: list[dict]) -> Change | None:
    if len(rows) > 1:
        return Change("conflict", name, f"{len(rows)} rows share this key; left alone")
    if not rows:
        return Change("create", name, f"value {setter['value']!r}")

    row = rows[0]
    if cstr(row.value) == cstr(setter["value"]):
        return None
    if not row.is_system_generated:
        return Change("keep", name, f"client value {row.value!r}, code value {setter['value']!r}")
    return Change("update", name, f"{row.value!r} -> {setter['value']!r}")


def _get_rows(setter: dict) -> list[dict]:
    return frappe.get_all(
        "Property Setter",
        filters={
            "doc_type": setter["doctype"],
            "property": setter["property"],
            "field_name": setter["fieldname"] or ["is", "not set"],
            "row_name": setter["row_name"] or ["is", "not set"],
        },
        fields=["name", "value", "is_system_generated"],
    )
