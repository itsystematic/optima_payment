"""Create declared custom fields and update the app-owned ones that drifted from code."""

from __future__ import annotations

import frappe
from frappe.utils import cstr
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from .report import Change


def sync(declared: dict[str, list[dict]], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    to_apply: dict[str, list[dict]] = {}
    rows = get_rows(declared)

    for doctype, fields in declared.items():
        if not frappe.db.exists("DocType", doctype):
            changes.append(Change("missing", doctype, "doctype is not on this site"))
            continue

        for field in fields:
            change = _plan(doctype, field, rows.get((doctype, field["fieldname"])))
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


def get_rows(declared: dict[str, list[dict]]) -> dict[tuple[str, str], dict]:
    """Return the site's Custom Field rows for the declared doctypes, keyed by (doctype, fieldname)."""
    if not declared:
        return {}
    rows = frappe.get_all("Custom Field", filters={"dt": ["in", list(declared)]}, fields=["*"])
    return {(row.dt, row.fieldname): row for row in rows}


def get_differences(row: dict, declaration: dict) -> dict[str, tuple]:
    """Return ``{key: (site value, code value)}`` for every declared key the row holds differently."""
    return {
        key: (row.get(key), value)
        for key, value in declaration.items()
        if key != "fieldname" and cstr(row.get(key)) != cstr(value)
    }


def _plan(doctype: str, field: dict, row: dict | None) -> Change | None:
    target = f"{doctype}.{field['fieldname']}"
    if not row:
        return Change("create", target)

    if not row.is_system_generated:
        return Change("keep", target, "is_system_generated=0, holds client edits until adopted")

    differences = get_differences(row, field)
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


def _describe_differences(differences: dict[str, tuple]) -> str:
    return ", ".join(f"{key}: {site!r} -> {code!r}" for key, (site, code) in differences.items())
