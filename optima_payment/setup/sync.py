"""Bring a site's Optima Payment custom fields and property setters in line with the feature
declarations, without overwriting what the client changed in Customize Form.

Ownership follows Frappe v15's ``is_system_generated`` flag:

- A declared Custom Field row at flag 1 belongs to the app. Customize Form saves client edits to
  such a field as separate Property Setters, so updating the row loses nothing. A row still at
  flag 0 holds client edits in place, so it is left alone until it has been adopted.
- A declared Property Setter belongs to the app only while its row keeps flag 1. When the client
  edits the same key in Customize Form, Frappe replaces the row with a flag-0 one.
- ``field_order`` stores a doctype's whole layout, so it is never synced.
- A fieldtype change is never applied in place; it is reported as a conflict.
"""

from __future__ import annotations

from dataclasses import dataclass

import click

import frappe
from frappe.utils import cstr
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from optima_payment.setup.registry import get_enabled_features

LAYOUT_PROPERTY = "field_order"

ACTION_COLORS = {
    "create": "green",
    "update": "cyan",
    "keep": "white",
    "conflict": "red",
    "missing": "yellow",
}


class DeclarationConflict(Exception):
    """Two declarations of the same field or property setter disagree on a value."""


@dataclass(frozen=True)
class Change:
    """One planned or applied change, as shown in the sync report."""

    action: str
    target: str
    detail: str = ""

    def __str__(self) -> str:
        suffix = f"  {self.detail}" if self.detail else ""
        return f"{self.action:<8} {self.target}{suffix}"


def sync(dry_run: bool = False) -> list[Change]:
    """Create missing customizations and update app-owned ones that drifted from their declaration."""
    changes = _sync_custom_fields(get_declared_custom_fields(), dry_run)
    changes += _sync_property_setters(get_declared_property_setters(), dry_run)
    _report("Optima Payment customization sync", changes, dry_run)
    return changes


def preview() -> list[Change]:
    """Show what ``sync`` would change on this site without writing anything."""
    return sync(dry_run=True)


def get_declared_custom_fields() -> dict[str, list[dict]]:
    """Merge custom fields from enabled features, grouped by doctype.

    A field declared more than once is combined into one declaration; the same key declared with
    two different values raises ``DeclarationConflict``.
    """
    merged: dict[tuple[str, str], dict] = {}
    for feature in get_enabled_features():
        if not feature.get_custom_fields:
            continue
        for doctype, fields in feature.get_custom_fields().items():
            for field in fields:
                key = (doctype, field["fieldname"])
                merged[key] = _merge_declarations(
                    merged.get(key, {}), field, f"{doctype}.{field['fieldname']}"
                )

    declared: dict[str, list[dict]] = {}
    for (doctype, _fieldname), field in merged.items():
        declared.setdefault(doctype, []).append(field)
    return declared


def get_declared_property_setters() -> list[dict]:
    """Merge property setters from enabled features into one declaration per key."""
    merged: dict[tuple[str, str, str, str], dict] = {}
    for feature in get_enabled_features():
        if not feature.get_property_setters:
            continue
        for declaration in feature.get_property_setters():
            setter = _normalize_property_setter(declaration)
            key = (
                setter["doctype"],
                setter["fieldname"] or "",
                setter["row_name"] or "",
                setter["property"],
            )
            merged[key] = _merge_declarations(
                merged.get(key, {}), setter, _property_setter_name(setter)
            )
    return list(merged.values())


def _merge_declarations(existing: dict, declaration: dict, target: str) -> dict:
    for key, value in declaration.items():
        if key in existing and cstr(existing[key]) != cstr(value):
            raise DeclarationConflict(
                f"{target}: '{key}' is declared as {existing[key]!r} and as {value!r}"
            )
    return {**existing, **declaration}


def _normalize_property_setter(declaration: dict) -> dict:
    fieldname = declaration.get("fieldname")
    return {
        "doctype": declaration["doctype"],
        "doctype_or_field": declaration.get("doctype_or_field")
        or ("DocField" if fieldname else "DocType"),
        "fieldname": fieldname,
        "row_name": declaration.get("row_name"),
        "property": declaration["property"],
        "value": declaration["value"],
        "property_type": declaration.get("property_type") or "Data",
    }


def _property_setter_name(setter: dict) -> str:
    return f"{setter['doctype']}-{setter['fieldname'] or setter['row_name'] or 'main'}-{setter['property']}"


def _sync_custom_fields(declared: dict[str, list[dict]], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    to_apply: dict[str, list[dict]] = {}
    rows = _get_custom_field_rows(declared)

    for doctype, fields in declared.items():
        if not frappe.db.exists("DocType", doctype):
            changes.append(Change("missing", doctype, "doctype is not on this site"))
            continue

        for field in fields:
            change = _plan_custom_field(doctype, field, rows.get((doctype, field["fieldname"])))
            if not change:
                continue
            changes.append(change)
            if change.action in ("create", "update"):
                to_apply.setdefault(doctype, []).append(field)

    if to_apply and not dry_run:
        # Doctype-wide validation also checks the client's own customizations; a problem there
        # must not block install or migrate.
        create_custom_fields(to_apply, ignore_validate=True, update=True)

    return changes


def _plan_custom_field(doctype: str, field: dict, row: dict | None) -> Change | None:
    target = f"{doctype}.{field['fieldname']}"
    if not row:
        return Change("create", target)

    if not row.is_system_generated:
        return Change("keep", target, "is_system_generated=0, holds client edits until adopted")

    differences = _get_differences(row, field)
    if "fieldtype" in differences:
        site_fieldtype, code_fieldtype = differences["fieldtype"]
        return Change(
            "conflict",
            target,
            f"fieldtype is {site_fieldtype!r} on the site and {code_fieldtype!r} in code; not changed in place",
        )
    if differences:
        return Change("update", target, _describe_differences(differences))
    return None


def _get_differences(row: dict, declaration: dict) -> dict[str, tuple]:
    return {
        key: (row.get(key), value)
        for key, value in declaration.items()
        if key != "fieldname" and cstr(row.get(key)) != cstr(value)
    }


def _describe_differences(differences: dict[str, tuple]) -> str:
    return ", ".join(f"{key}: {site!r} -> {code!r}" for key, (site, code) in differences.items())


def _get_custom_field_rows(declared: dict[str, list[dict]]) -> dict[tuple[str, str], dict]:
    if not declared:
        return {}
    rows = frappe.get_all("Custom Field", filters={"dt": ["in", list(declared)]}, fields=["*"])
    return {(row.dt, row.fieldname): row for row in rows}


def _sync_property_setters(declared: list[dict], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    updated_doctypes: set[str] = set()

    for setter in declared:
        if setter["property"] == LAYOUT_PROPERTY:
            continue

        name = _property_setter_name(setter)
        if not frappe.db.exists("DocType", setter["doctype"]):
            changes.append(Change("missing", name, "doctype is not on this site"))
            continue

        rows = _get_property_setter_rows(setter)
        change = _plan_property_setter(name, setter, rows)
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


def _plan_property_setter(name: str, setter: dict, rows: list[dict]) -> Change | None:
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


def _get_property_setter_rows(setter: dict) -> list[dict]:
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


def _report(title: str, changes: list[Change], dry_run: bool) -> None:
    mode = "preview, nothing written" if dry_run else "applied"
    click.secho(f"{title} ({mode}): {len(changes)} item(s)", fg="blue")
    for change in changes:
        click.secho(f"   {change}", fg=ACTION_COLORS[change.action])
