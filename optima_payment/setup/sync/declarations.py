"""Collect what the enabled features declare, merged into one declaration per key."""

from __future__ import annotations

from frappe.utils import cstr

from optima_payment.setup.registry import get_enabled_features


class DeclarationConflict(Exception):
    """Two declarations of the same field or property setter disagree on a value."""


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
    for (doctype, _), field in merged.items():
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
                merged.get(key, {}), setter, property_setter_name(setter)
            )
    return list(merged.values())


def property_setter_name(setter: dict) -> str:
    return f"{setter['doctype']}-{setter['fieldname'] or setter['row_name'] or 'main'}-{setter['property']}"


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
