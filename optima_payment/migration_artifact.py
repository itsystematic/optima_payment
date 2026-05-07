import json
from pathlib import Path

import frappe
from click import secho

from optima_payment.patches.payment_entry_legacy_to_modern import (
    COMPANY_EXPENSE_CHILD_DOCTYPE,
    COMPANY_EXPENSE_CHILD_FIELDS,
    LEGACY_COMPANY_EXPENSE_FIELD,
    LEGACY_MULTI_EXPENSE_FIELD,
    LEGACY_TOTAL_AMOUNT_FIELD,
    MODERN_COMPANY_EXPENSE_FIELD,
    MODERN_MULTI_EXPENSE_FIELD,
    MODERN_TOTAL_AMOUNT_FIELD,
    backfill_entries_from_company_expense_rows,
)

ARTIFACT_DIRECTORY = ("private", "files", "optima_payment")
ARTIFACT_FILENAME = "cheque_legacy_export.json"


def import_cheque_legacy_artifact() -> dict:
    artifact_path = Path(get_artifact_path())
    if not artifact_path.exists():
        secho("No cheque legacy export artifact found; skipping legacy import", fg="yellow")
        return {"artifact_found": False, "payment_entries": 0, "company_expense_rows": 0}

    artifact = json.loads(artifact_path.read_text())
    payment_entries = artifact.get("payment_entries", [])

    imported_payment_entries = import_payment_entries(payment_entries)
    imported_company_expense_rows = import_company_expense_rows(payment_entries)
    backfilled_entries = backfill_entries_from_company_expense_rows()

    frappe.db.commit()
    frappe.clear_cache(doctype="Payment Entry")
    frappe.clear_cache(doctype=COMPANY_EXPENSE_CHILD_DOCTYPE)

    secho(
        "Imported cheque legacy export artifact "
        f"(payment_entries={imported_payment_entries}, company_expense_rows={imported_company_expense_rows}, "
        f"row_backfills={backfilled_entries})",
        fg="green",
    )
    return {
        "artifact_found": True,
        "payment_entries": imported_payment_entries,
        "company_expense_rows": imported_company_expense_rows,
        "row_backfills": backfilled_entries,
    }


def get_artifact_path() -> str:
    return frappe.get_site_path(*ARTIFACT_DIRECTORY, ARTIFACT_FILENAME)


def import_payment_entries(payment_entries: list[dict]) -> int:
    if not payment_entries:
        return 0

    imported = 0
    for payment_entry in payment_entries:
        if not frappe.db.exists("Payment Entry", payment_entry["name"]):
            continue

        values = {}
        existing_values = frappe.db.get_value(
            "Payment Entry",
            payment_entry["name"],
            [field for field in (MODERN_MULTI_EXPENSE_FIELD, MODERN_TOTAL_AMOUNT_FIELD) if frappe.db.has_column("Payment Entry", field)],
            as_dict=True,
        ) or {}

        if (
            frappe.db.has_column("Payment Entry", MODERN_MULTI_EXPENSE_FIELD)
            and payment_entry.get(LEGACY_MULTI_EXPENSE_FIELD)
            and not existing_values.get(MODERN_MULTI_EXPENSE_FIELD)
        ):
            values[MODERN_MULTI_EXPENSE_FIELD] = 1

        if (
            frappe.db.has_column("Payment Entry", MODERN_TOTAL_AMOUNT_FIELD)
            and frappe.utils.flt(payment_entry.get(LEGACY_TOTAL_AMOUNT_FIELD))
            and not frappe.utils.flt(existing_values.get(MODERN_TOTAL_AMOUNT_FIELD))
        ):
            values[MODERN_TOTAL_AMOUNT_FIELD] = payment_entry.get(LEGACY_TOTAL_AMOUNT_FIELD)

        if values:
            frappe.db.set_value("Payment Entry", payment_entry["name"], values, update_modified=False)
            imported += 1

    return imported


def import_company_expense_rows(payment_entries: list[dict]) -> int:
    parent_names = [payment_entry["name"] for payment_entry in payment_entries if payment_entry.get(LEGACY_COMPANY_EXPENSE_FIELD)]
    if not parent_names:
        return 0

    existing_rows = frappe.get_all(
        COMPANY_EXPENSE_CHILD_DOCTYPE,
        filters={
            "parenttype": "Payment Entry",
            "parentfield": MODERN_COMPANY_EXPENSE_FIELD,
            "parent": ["in", parent_names],
        },
        fields=["name", "parent", "idx"],
    )
    rows_by_parent_idx = {
        (row.parent, int(row.idx)): row.name
        for row in existing_rows
    }

    imported = 0
    for payment_entry in payment_entries:
        for row in payment_entry.get(LEGACY_COMPANY_EXPENSE_FIELD, []):
            key = (payment_entry["name"], int(row["idx"]))
            if key in rows_by_parent_idx:
                existing_name = rows_by_parent_idx[key]
                updates = {
                    fieldname: row.get(fieldname)
                    for fieldname in COMPANY_EXPENSE_CHILD_FIELDS
                    if frappe.db.get_value(COMPANY_EXPENSE_CHILD_DOCTYPE, existing_name, fieldname) != row.get(fieldname)
                }
                if updates:
                    frappe.db.set_value(COMPANY_EXPENSE_CHILD_DOCTYPE, existing_name, updates, update_modified=False)
                continue

            child_doc = frappe.get_doc(
                {
                    "doctype": COMPANY_EXPENSE_CHILD_DOCTYPE,
                    "parent": payment_entry["name"],
                    "parenttype": "Payment Entry",
                    "parentfield": MODERN_COMPANY_EXPENSE_FIELD,
                    "idx": row["idx"],
                    **{fieldname: row.get(fieldname) for fieldname in COMPANY_EXPENSE_CHILD_FIELDS},
                }
            )
            child_doc.flags.ignore_permissions = True
            child_doc.db_insert()
            imported += 1

    return imported
