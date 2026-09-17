"""Create declared property setters and update the app-owned ones that drifted from code."""

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
