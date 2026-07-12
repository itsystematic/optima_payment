"""Rename letter_of_credit_account → providing_letter_of_credit_account on Bank Account.

The single LC account field has been split into two directional fields:
  - providing_letter_of_credit_account  (was: letter_of_credit_account)
  - receiving_letter_of_credit_account  (new)

Existing data in letter_of_credit_account is migrated to
providing_letter_of_credit_account before the old field is removed.
"""

import click
import frappe

from optima_payment.setup.features import banking
from optima_payment.setup.metadata import create_custom_fields_safely, sync_custom_field_schema

OLD_FIELDNAME = "letter_of_credit_account"
NEW_FIELDNAME = "providing_letter_of_credit_account"


def execute() -> None:
    _migrate_existing_data()
    _remove_old_custom_field()

    custom_fields = {"Bank Account": banking.get_custom_fields()["Bank Account"]}
    create_custom_fields_safely(custom_fields)
    sync_custom_field_schema(custom_fields)

    click.secho(
        "Renamed letter_of_credit_account → providing_letter_of_credit_account "
        "and added receiving_letter_of_credit_account on Bank Account",
        fg="green",
    )


def _migrate_existing_data() -> None:
    """Copy letter_of_credit_account values into providing_letter_of_credit_account."""
    if not frappe.db.has_column("Bank Account", OLD_FIELDNAME):
        return

    frappe.db.sql(
        f"""
        UPDATE `tabBank Account`
        SET `{NEW_FIELDNAME}` = `{OLD_FIELDNAME}`
        WHERE `{OLD_FIELDNAME}` IS NOT NULL AND `{OLD_FIELDNAME}` != ''
        """
    )
    click.secho(f"Migrated {OLD_FIELDNAME} → {NEW_FIELDNAME} for existing Bank Account records", fg="cyan")


def _remove_old_custom_field() -> None:
    old_cf_name = frappe.db.get_value(
        "Custom Field", {"dt": "Bank Account", "fieldname": OLD_FIELDNAME}, "name"
    )
    if old_cf_name:
        frappe.delete_doc("Custom Field", old_cf_name, force=True)
        frappe.clear_cache(doctype="Bank Account")
        click.secho(f"Deleted obsolete Custom Field: {old_cf_name}", fg="cyan")
