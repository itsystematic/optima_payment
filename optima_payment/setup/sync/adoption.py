"""One-time move of declared custom fields from is_system_generated=0 to 1 without changing the form.

A declared property the site holds with a value different from code may be a client edit, so that
value is first kept as a flag-0 Property Setter, the same record Customize Form writes for flag-1
fields, unless a property setter already overrides it. Only then is the row reset to the
declaration and flagged 1.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.customize_form.customize_form import docfield_properties

from .custom_fields import get_differences, get_rows
from .report import Change

# Frappe's Meta honours an insert_after property setter even though Customize Form never writes one.
PRESERVABLE_PROPERTIES = {**docfield_properties, "insert_after": "Data"}


def adopt(declared: dict[str, list[dict]], dry_run: bool) -> list[Change]:
    rows = get_rows(declared)
    changes: list[Change] = []
    adopted_doctypes: set[str] = set()

    for doctype, fields in declared.items():
        for field in fields:
            row = rows.get((doctype, field["fieldname"]))
            if not row or row.is_system_generated:
                continue

            change, differences, kept_as_setters = _plan(doctype, field, row)
            changes.append(change)
            if dry_run or change.action != "adopt":
                continue

            for key in kept_as_setters:
                frappe.make_property_setter(
                    {
                        "doctype": doctype,
                        "doctype_or_field": "DocField",
                        "fieldname": field["fieldname"],
                        "property": key,
                        "value": row.get(key),
                        "property_type": PRESERVABLE_PROPERTIES[key],
                    },
                    validate_fields_for_doctype=False,
                    is_system_generated=False,
                )
            frappe.db.set_value(
                "Custom Field",
                row.name,
                {**{key: field[key] for key in differences}, "is_system_generated": 1},
                update_modified=False,
            )
            adopted_doctypes.add(doctype)

    for doctype in adopted_doctypes:
        frappe.clear_cache(doctype=doctype)

    return changes


def _plan(doctype: str, field: dict, row: dict) -> tuple[Change, dict[str, tuple], list[str]]:
    target = f"{doctype}.{field['fieldname']}"
    differences = get_differences(row, field)

    if "fieldtype" in differences:
        site_fieldtype, code_fieldtype = differences["fieldtype"]
        return (
            Change(
                "conflict",
                target,
                f"fieldtype is {site_fieldtype!r} on the site and {code_fieldtype!r} in code; left at is_system_generated=0",
            ),
            {},
            [],
        )

    unsupported = [key for key in differences if key not in PRESERVABLE_PROPERTIES]
    if unsupported:
        return (
            Change(
                "conflict",
                target,
                f"site value of {', '.join(unsupported)} cannot be kept as a property setter; left at is_system_generated=0",
            ),
            {},
            [],
        )

    overridden = [
        key for key in differences if _has_field_property_setter(doctype, field["fieldname"], key)
    ]
    kept_as_setters = [key for key in differences if key not in overridden]

    details = [f"keeps site {key} {differences[key][0]!r} (code {differences[key][1]!r})" for key in kept_as_setters]
    details += [f"{key} already overridden by a property setter" for key in overridden]
    return Change("adopt", target, "; ".join(details)), differences, kept_as_setters


def _has_field_property_setter(doctype: str, fieldname: str, property_name: str) -> bool:
    return bool(
        frappe.db.exists(
            "Property Setter", {"doc_type": doctype, "field_name": fieldname, "property": property_name}
        )
    )
