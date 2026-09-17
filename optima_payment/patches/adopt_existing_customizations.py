"""Take ownership of Optima Payment customizations created before ownership was tracked, then sync.

Adoption changes nothing on the forms:
- Declared custom fields still at is_system_generated=0 move to 1. A property the site holds with a
  value different from code may be a client edit, so it is first kept as a flag-0 property setter.
- Declared property setters at flag 0 that hold exactly the declared value move to flag 1. They came
  from old imports; from now on app changes to them reach the site. field_order is left alone.

Sites where the Letter of Credit rename ran with its old code still have letter_of_credit_account
and lack the providing/receiving fields, so the fixed rename patch runs again there.

sync() then creates missing customizations and updates the app-owned ones that drifted from code.

Adoption lives only in this patch, not in setup.sync, so no later patch can run it again against
customizations the client makes after this point.
"""

from __future__ import annotations

import frappe
from frappe.utils import cstr
from frappe.custom.doctype.customize_form.customize_form import docfield_properties

from optima_payment.patches import rename_lc_account_to_providing_and_add_receiving as lc_account_rename
from optima_payment.setup.sync import sync
from optima_payment.setup.sync.custom_fields import get_differences, get_rows as get_custom_field_rows
from optima_payment.setup.sync.declarations import get_declared_custom_fields, get_declared_property_setters
from optima_payment.setup.sync.property_setters import FIELD_ORDER_PROPERTY, get_rows as get_property_setter_rows
from optima_payment.setup.sync.report import Change, report

# Frappe's Meta honours an insert_after property setter even though Customize Form never writes one.
PRESERVABLE_PROPERTIES = {**docfield_properties, "insert_after": "Data"}


def execute() -> None:
    adopt_custom_fields()
    adopt_property_setters()

    if frappe.db.exists("Custom Field", {"dt": "Bank Account", "fieldname": lc_account_rename.OLD_FIELDNAME}):
        lc_account_rename.execute()

    sync()


def adopt_custom_fields(dry_run: bool = False) -> list[Change]:
    """Move declared custom fields still at flag 0 to flag 1 without changing the form.

    A declared property the site holds with a value different from code is first kept as a flag-0
    Property Setter, the same record Customize Form writes for flag-1 fields, unless a property
    setter already overrides it. Only then is the row reset to the declaration and flagged 1.
    """
    declared = get_declared_custom_fields()
    rows = get_custom_field_rows(declared)
    changes: list[Change] = []
    adopted_doctypes: set[str] = set()

    for doctype, fields in declared.items():
        for field in fields:
            row = rows.get((doctype, field["fieldname"]))
            if not row or row.is_system_generated:
                continue

            change, differences, kept_as_setters = _plan_custom_field_adoption(doctype, field, row)
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

    report("Optima Payment custom field adoption", changes, dry_run)
    return changes


def adopt_property_setters(dry_run: bool = False) -> list[Change]:
    """Move declared property setters at flag 0 that hold exactly the declared value to flag 1.

    Only the flag changes, so the form stays the same.
    """
    changes: list[Change] = []
    for setter in get_declared_property_setters():
        if setter["property"] == FIELD_ORDER_PROPERTY:
            continue

        rows = get_property_setter_rows(setter)
        if len(rows) != 1 or rows[0].is_system_generated or cstr(rows[0].value) != cstr(setter["value"]):
            continue

        changes.append(Change("adopt", rows[0].name, "is_system_generated=0 but holds the code value"))
        if not dry_run:
            frappe.db.set_value("Property Setter", rows[0].name, "is_system_generated", 1, update_modified=False)

    report("Optima Payment property setter adoption", changes, dry_run)
    return changes


def _plan_custom_field_adoption(doctype: str, field: dict, row: dict) -> tuple[Change, dict[str, tuple], list[str]]:
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
