"""Move legacy Bank Guarantee account defaults from Company to app settings."""

from typing import Optional

import frappe
from click import secho


LEGACY_TO_SETTING_FIELD_MAP = {
    "default_insurance_account": "bank_guarantee_insurance_account",
    "default_receiving_insurance_account": "bank_guarantee_receiving_insurance_account",
    "bank_fees_account": "bank_guarantee_bank_fees_account",
}

LEGACY_LOSS_EXPENSE_FIELDS = (
    "lost_expense_bank_guarantee_account",
    "lost_expense_Bank_guarantee_account",
)


def _get_existing_company_fields() -> dict[str, str]:
    existing_company_fields = {
        old_field: new_field
        for old_field, new_field in LEGACY_TO_SETTING_FIELD_MAP.items()
        if frappe.db.has_column("Company", old_field)
    }

    # Older installs used inconsistent casing for this custom field name.
    loss_expense_field: Optional[str] = next(
        (
            fieldname
            for fieldname in LEGACY_LOSS_EXPENSE_FIELDS
            if frappe.db.has_column("Company", fieldname)
        ),
        None,
    )
    if loss_expense_field:
        existing_company_fields[loss_expense_field] = "bank_guarantee_loss_expense_account"

    return existing_company_fields


def execute() -> None:
    """Copy legacy Company values into per-company Optima Payment settings."""

    existing_company_fields = _get_existing_company_fields()
    if not existing_company_fields:
        return

    companies = frappe.get_all("Company", fields=["name", *existing_company_fields])
    setting_names_by_company = {
        row.company: row.name
        for row in frappe.get_all("Optima Payment Setting", fields=["name", "company"])
    }

    updated_settings = 0
    migrated_values = 0

    for company in companies:
        setting_name = setting_names_by_company.get(company.name)
        if not setting_name:
            continue

        current_setting_values = frappe.db.get_value(
            "Optima Payment Setting",
            setting_name,
            list(existing_company_fields.values()),
            as_dict=True,
        )
        if not current_setting_values:
            continue

        values_to_update = {}
        for old_field, new_field in existing_company_fields.items():
            legacy_value = company.get(old_field)
            if not legacy_value or current_setting_values.get(new_field):
                continue

            values_to_update[new_field] = legacy_value

        if not values_to_update:
            continue

        frappe.db.set_value(
            "Optima Payment Setting",
            setting_name,
            values_to_update,
            update_modified=False,
        )
        updated_settings += 1
        migrated_values += len(values_to_update)

    secho(
        "Migrated Bank Guarantee account settings "
        f"(settings={updated_settings}, values={migrated_values})",
        fg="green",
    )
