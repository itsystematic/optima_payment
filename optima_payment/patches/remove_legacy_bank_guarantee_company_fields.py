"""Remove obsolete Company custom fields after Bank Guarantee settings migration."""

import click
import frappe

from optima_payment.setup.metadata import cleanup_custom_fields


FIELD_MAPPINGS = (
    ("default_insurance_account", "bank_guarantee_insurance_account"),
    ("default_receiving_insurance_account", "bank_guarantee_receiving_insurance_account"),
    ("bank_fees_account", "bank_guarantee_bank_fees_account"),
)

LOSS_EXPENSE_SOURCE_FIELDS = (
    "lost_expense_bank_guarantee_account",
    "lost_expense_Bank_guarantee_account",
)


def _get_removable_company_fields() -> list[str]:
    """Return legacy Company fields whose values are already present in settings."""

    removable_fields = [
        source_field
        for source_field, target_field in FIELD_MAPPINGS
        if _can_remove_field(source_field, target_field)
    ]

    if _can_remove_loss_expense_fields():
        removable_fields.extend(
            fieldname
            for fieldname in LOSS_EXPENSE_SOURCE_FIELDS
            if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": fieldname})
        )

    return removable_fields


def _can_remove_field(source_field: str, target_field: str) -> bool:
    if not frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": source_field}):
        return False

    for company_name in frappe.get_all("Company", pluck="name"):
        source_value = frappe.db.get_value("Company", company_name, source_field)
        if not source_value:
            continue

        target_value = frappe.db.get_value(
            "Optima Payment Setting",
            {"company": company_name},
            target_field,
        )
        if not target_value:
            click.secho(
                f"Skipping removal of Company.{source_field} because "
                f"{company_name} is missing Optima Payment Setting.{target_field}",
                fg="yellow",
            )
            return False

    return True


def _can_remove_loss_expense_fields() -> bool:
    existing_loss_fields = [
        fieldname
        for fieldname in LOSS_EXPENSE_SOURCE_FIELDS
        if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": fieldname})
    ]
    if not existing_loss_fields:
        return False

    # Older sites may have either casing variant; treat both as the same legacy source.
    for company_name in frappe.get_all("Company", pluck="name"):
        source_values = [
            frappe.db.get_value("Company", company_name, fieldname)
            for fieldname in existing_loss_fields
        ]
        if not any(source_values):
            continue

        target_value = frappe.db.get_value(
            "Optima Payment Setting",
            {"company": company_name},
            "bank_guarantee_loss_expense_account",
        )
        if not target_value:
            click.secho(
                "Skipping removal of legacy Bank Guarantee loss expense fields because "
                f"{company_name} is missing Optima Payment Setting.bank_guarantee_loss_expense_account",
                fg="yellow",
            )
            return False

    return True


def execute() -> None:
    """Delete migrated Company custom fields that are no longer used by the app."""

    removable_fields = _get_removable_company_fields()
    if not removable_fields:
        click.secho("No legacy Bank Guarantee Company fields to remove", fg="yellow")
        return

    removed = cleanup_custom_fields(
        {
            "Company": [{"fieldname": fieldname} for fieldname in removable_fields],
        }
    )
    click.secho(f"Removed {removed} legacy Bank Guarantee Company custom fields", fg="green")
