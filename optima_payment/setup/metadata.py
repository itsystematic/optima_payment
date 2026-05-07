"""Generic metadata helpers shared by Optima Payment setup features."""

from __future__ import annotations

from collections.abc import Iterable

import click
import frappe
from frappe import make_property_setter


def merge_custom_fields(*sections: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Merge custom field maps while preserving doctype grouping."""
    custom_fields: dict[str, list[dict]] = {}
    for section in sections:
        for doctype, fields in section.items():
            custom_fields.setdefault(doctype, []).extend(fields)

    return custom_fields


def create_custom_fields_safely(custom_fields: dict[str, list[dict]]) -> None:
    """Validate and upsert custom fields for a feature."""
    if not custom_fields:
        click.secho("No custom fields to create", fg="yellow")
        return

    validated_fields = validate_custom_fields_data(custom_fields)
    if not validated_fields:
        click.secho("No valid custom fields found after validation", fg="yellow")
        return

    upsert_custom_fields(validated_fields)
    click.secho(
        f"Successfully created custom fields for {len(validated_fields)} DocTypes",
        fg="green",
    )


def sync_custom_field_schema(custom_fields: dict[str, list[dict]]) -> None:
    """Force database schema sync for doctypes that received Optima fields."""
    for doctype in get_custom_field_doctypes(custom_fields):
        frappe.clear_cache(doctype=doctype)
        frappe.db.updatedb(doctype)
        click.secho(f"Synchronized schema for {doctype}", fg="green")


def get_custom_field_doctypes(custom_fields: dict[str, list[dict]]) -> list[str]:
    """Return doctypes that own the provided custom fields."""
    doctypes: list[str] = []
    for doctype in custom_fields:
        if isinstance(doctype, str):
            doctypes.append(doctype)
        else:
            doctypes.extend(list(doctype))

    return list(dict.fromkeys(doctypes))


def validate_custom_fields_data(custom_fields: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Filter out malformed custom field definitions before applying them."""
    validated_fields: dict[str, list[dict]] = {}

    for doctype, fields in custom_fields.items():
        if not doctype or not fields:
            click.secho(f"Skipping invalid DocType: {doctype}", fg="yellow")
            continue

        valid_fields = []
        for field in fields:
            if not field or not isinstance(field, dict):
                click.secho(f"Skipping invalid field in {doctype}: {field}", fg="yellow")
                continue

            if not field.get("fieldname") or not field.get("fieldtype"):
                click.secho(
                    f"Skipping field with missing required properties in {doctype}: {field}",
                    fg="yellow",
                )
                continue

            valid_fields.append(field)

        if valid_fields:
            validated_fields[doctype] = valid_fields

    return validated_fields


def upsert_custom_fields(custom_fields: dict[str, list[dict]]) -> None:
    """Create or update the provided custom fields."""
    for doctype, fields in custom_fields.items():
        for field in fields:
            upsert_custom_field(doctype, field)


def upsert_custom_field(doctype: str, field: dict) -> None:
    """Upsert a single custom field while preserving fieldtype integrity."""
    existing_field = frappe.db.get_value(
        "Custom Field",
        {"dt": doctype, "fieldname": field.get("fieldname")},
        ["name", "fieldtype"],
        as_dict=True,
    )
    target_fieldtype = field.get("fieldtype")

    if existing_field and existing_field.fieldtype != target_fieldtype:
        frappe.delete_doc("Custom Field", existing_field.name, force=True)
        frappe.clear_cache(doctype=doctype)
        click.secho(
            f"Recreated conflicting custom field {doctype}.{field.get('fieldname')} "
            f"({existing_field.fieldtype} -> {target_fieldtype})",
            fg="yellow",
        )
        existing_field = None

    if existing_field:
        custom_field = frappe.get_doc("Custom Field", existing_field.name)
        updates = {}
        for key, value in field.items():
            if custom_field.get(key) != value:
                updates[key] = value

        if updates:
            frappe.db.set_value("Custom Field", existing_field.name, updates, update_modified=False)
            frappe.clear_cache(doctype=doctype)
        return

    custom_field = frappe.get_doc({"doctype": "Custom Field", "dt": doctype, **field})
    custom_field.insert(ignore_permissions=True)


def add_property_setters(property_setters: list[dict]) -> None:
    """Create or update property setters for a feature."""
    if not property_setters:
        click.secho("No property setters to create", fg="yellow")
        return

    processed_doctypes: set[str] = set()
    for property_setter in property_setters:
        if not property_setter or not isinstance(property_setter, dict):
            click.secho(f"Skipping invalid property setter: {property_setter}", fg="yellow")
            continue

        result = upsert_property_setter(property_setter)
        if property_setter.get("doctype"):
            processed_doctypes.add(property_setter["doctype"])
        click.secho(
            f"{result.title()} property setter for: {property_setter.get('doctype', 'Unknown')}",
            fg="green",
        )

    for doctype in processed_doctypes:
        frappe.clear_cache(doctype=doctype)


def cleanup_property_setters(property_setters: list[dict]) -> int:
    """Remove property setters that exactly match feature ownership filters."""
    removed = 0
    for property_setter in property_setters:
        existing_names = frappe.get_all(
            "Property Setter",
            filters=get_property_setter_filters(property_setter),
            pluck="name",
        )
        for name in existing_names:
            frappe.delete_doc("Property Setter", name, force=True)
            removed += 1

    for property_setter in property_setters:
        if property_setter.get("doctype"):
            frappe.clear_cache(doctype=property_setter["doctype"])

    return removed


def cleanup_custom_fields(custom_fields: dict[str, list[dict]]) -> int:
    """Remove custom fields owned by a feature."""
    removed = 0
    for doctype, fields in custom_fields.items():
        fieldnames = [field.get("fieldname") for field in fields if field.get("fieldname")]
        if not fieldnames:
            continue

        existing_names = frappe.get_all(
            "Custom Field",
            filters={"dt": doctype, "fieldname": ["in", fieldnames]},
            pluck="name",
        )
        for name in existing_names:
            frappe.delete_doc("Custom Field", name, force=True)
            removed += 1

        frappe.clear_cache(doctype=doctype)

    return removed


def cleanup_obsolete_property_setters(property_setters: Iterable[dict]) -> None:
    """Remove obsolete property setters that should not survive Optima setup."""
    removed = cleanup_property_setters(list(property_setters))
    if removed:
        click.secho(f"Removed {removed} obsolete property setters", fg="yellow")


def upsert_property_setter(property_setter: dict) -> str:
    """Create, update, or verify a property setter."""
    normalized_property_setter = dict(property_setter)
    normalized_property_setter.setdefault("doctype_or_field", "DocField")
    normalized_property_setter.setdefault("property_type", "Data")

    filters = get_property_setter_filters(normalized_property_setter)
    existing_names = frappe.get_all("Property Setter", filters=filters, pluck="name")
    primary_name = existing_names[0] if existing_names else None

    for duplicate_name in existing_names[1:]:
        frappe.delete_doc("Property Setter", duplicate_name, force=True)

    if not primary_name:
        make_property_setter(normalized_property_setter)
        return "created"

    property_setter_doc = frappe.get_doc("Property Setter", primary_name)
    updates = {}
    field_mapping = {
        "doctype_or_field": "doctype_or_field",
        "fieldname": "field_name",
        "row_name": "row_name",
        "value": "value",
        "property_type": "property_type",
    }

    for source_key, target_key in field_mapping.items():
        new_value = normalized_property_setter.get(source_key)
        if property_setter_doc.get(target_key) != new_value:
            updates[target_key] = new_value

    if updates:
        frappe.db.set_value("Property Setter", primary_name, updates, update_modified=False)
        frappe.clear_cache(doctype=normalized_property_setter.get("doctype"))
        return "updated"

    return "verified"


def get_property_setter_filters(property_setter: dict) -> dict:
    """Build a unique-enough filter for a property setter definition."""
    filters = {
        "doc_type": property_setter.get("doctype"),
        "property": property_setter.get("property"),
    }

    if property_setter.get("fieldname"):
        filters["field_name"] = property_setter.get("fieldname")

    if property_setter.get("row_name"):
        filters["row_name"] = property_setter.get("row_name")

    return filters
