"""Record how every customized form looks, so a migrate can be checked for layout damage.

Run before and after a migrate::

    bench --site <site> execute optima_payment.setup.form_snapshot.save
    bench --site <site> migrate
    bench --site <site> execute optima_payment.setup.form_snapshot.diff

The snapshot covers every doctype that carries a custom field or a property setter, not only the
ones this app declares, so damage done by any app shows up.
"""

from __future__ import annotations

import json

import click

import frappe
from frappe.utils import now
from frappe.custom.doctype.customize_form.customize_form import docfield_properties, doctype_properties

from optima_payment.setup.sync.declarations import get_declared_custom_fields, get_declared_property_setters

DEFAULT_FILENAME = "optima-form-snapshot.json"
FIELD_PROPERTIES = ["fieldtype", "insert_after", *[key for key in docfield_properties if key != "idx"]]
DOCTYPE_PROPERTIES = [*doctype_properties, "field_order"]
MAX_REPORTED = 200
MAX_VALUE_LENGTH = 120


def save(path: str | None = None) -> None:
    """Write a snapshot of every customized form to ``path``."""
    path = path or frappe.get_site_path("private", "files", DEFAULT_FILENAME)
    with open(path, "w") as snapshot_file:
        json.dump(snapshot(), snapshot_file, indent=1, default=str)
    click.secho(f"Form snapshot written to {path}", fg="green")


def diff(path: str | None = None) -> None:
    """Compare the forms as they are now with the snapshot in ``path``."""
    path = path or frappe.get_site_path("private", "files", DEFAULT_FILENAME)
    with open(path) as snapshot_file:
        before = json.load(snapshot_file)

    # Round-trip the live snapshot so both sides have been through the same JSON conversion.
    differences = compare(before, json.loads(json.dumps(snapshot(), default=str)))
    click.secho(
        f"Comparing {len(before['doctypes'])} forms with the snapshot taken at {before['captured_at']}",
        fg="blue",
    )
    if not differences:
        click.secho("No differences.", fg="green")
        return

    click.secho(f"{len(differences)} difference(s):", fg="red")
    for line in differences[:MAX_REPORTED]:
        click.secho(f"   {line}", fg="red")
    if len(differences) > MAX_REPORTED:
        click.secho(f"   ... and {len(differences) - MAX_REPORTED} more", fg="red")


def snapshot(doctypes: list[str] | None = None) -> dict:
    """Return the current form layout and properties of every customized doctype."""
    doctypes = doctypes or get_customized_doctypes()
    return {
        "site": frappe.local.site,
        "captured_at": now(),
        "counts": _get_counts(),
        "doctypes": {doctype: _snapshot_doctype(doctype) for doctype in doctypes},
    }


def compare(before: dict, after: dict) -> list[str]:
    """Describe every layout or property difference between two snapshots."""
    differences: list[str] = []
    for doctype, was in before["doctypes"].items():
        now_ = after["doctypes"].get(doctype)
        if now_ is None:
            differences.append(f"{doctype}: no longer customized or missing from this site")
            continue

        if was["order"] != now_["order"]:
            differences.append(f"{doctype}: field order changed")
        for fieldname in set(was["fields"]) - set(now_["fields"]):
            differences.append(f"{doctype}.{fieldname}: field gone")
        for fieldname in set(now_["fields"]) - set(was["fields"]):
            differences.append(f"{doctype}.{fieldname}: field added")

        for fieldname, properties in was["fields"].items():
            current = now_["fields"].get(fieldname)
            if current is None:
                continue
            for key in sorted(set(properties) | set(current)):
                if properties.get(key) != current.get(key):
                    differences.append(
                        f"{doctype}.{fieldname}.{key}: {_short(properties.get(key))} -> {_short(current.get(key))}"
                    )

        for key in sorted(set(was["properties"]) | set(now_["properties"])):
            if was["properties"].get(key) != now_["properties"].get(key):
                differences.append(
                    f"{doctype}.{key}: {_short(was['properties'].get(key))} -> {_short(now_['properties'].get(key))}"
                )

    for doctype in set(after["doctypes"]) - set(before["doctypes"]):
        differences.append(f"{doctype}: newly customized")
    return differences


def get_customized_doctypes() -> list[str]:
    doctypes = set(frappe.get_all("Custom Field", pluck="dt", distinct=True))
    doctypes |= set(frappe.get_all("Property Setter", pluck="doc_type", distinct=True))
    doctypes |= set(get_declared_custom_fields())
    doctypes |= {setter["doctype"] for setter in get_declared_property_setters()}
    return sorted(doctype for doctype in doctypes if frappe.db.exists("DocType", doctype))


def _snapshot_doctype(doctype: str) -> dict:
    meta = frappe.get_meta(doctype, cached=False)
    return {
        "order": [df.fieldname for df in meta.fields],
        "fields": {df.fieldname: _set_properties(df, FIELD_PROPERTIES) for df in meta.fields},
        "properties": _set_properties(meta, DOCTYPE_PROPERTIES),
    }


def _short(value) -> str:
    text = repr(value)
    return text if len(text) <= MAX_VALUE_LENGTH else f"{text[:MAX_VALUE_LENGTH]}... ({len(text)} chars)"


def _set_properties(doc, keys: list[str]) -> dict:
    """Keep only properties that hold a value; an unset one is compared as missing."""
    return {key: doc.get(key) for key in keys if doc.get(key) not in (None, "")}


def _get_counts() -> dict:
    counts = {}
    for doctype in ("Custom Field", "Property Setter"):
        counts[doctype] = {
            "app owned (flag 1)": frappe.db.count(doctype, {"is_system_generated": 1}),
            "site owned (flag 0)": frappe.db.count(doctype, {"is_system_generated": 0}),
        }
    return counts
