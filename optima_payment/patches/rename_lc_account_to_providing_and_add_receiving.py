"""Rename letter_of_credit_account → providing_letter_of_credit_account on Bank Account.

The single LC account field has been split into two directional fields:
  - providing_letter_of_credit_account  (was: letter_of_credit_account)
  - receiving_letter_of_credit_account  (new)

The new fields are created first. letter_of_credit_account values are then copied into
providing_letter_of_credit_account wherever it is still empty, and only then is the old field removed.
"""

import click
import frappe

from optima_payment.setup.sync import sync

OLD_FIELDNAME = "letter_of_credit_account"
NEW_FIELDNAME = "providing_letter_of_credit_account"


def execute() -> None:
    sync()
    _migrate_existing_data()
    _remove_old_custom_field()

    click.secho(
        "Renamed letter_of_credit_account → providing_letter_of_credit_account "
        "and added receiving_letter_of_credit_account on Bank Account",
        fg="green",
    )


def _migrate_existing_data() -> None:
    """Copy letter_of_credit_account values into providing_letter_of_credit_account where it is empty."""
    if not frappe.db.has_column("Bank Account", OLD_FIELDNAME):
        return

    frappe.db.sql(
        f"""
        UPDATE `tabBank Account`
        SET `{NEW_FIELDNAME}` = `{OLD_FIELDNAME}`
        WHERE IFNULL(`{OLD_FIELDNAME}`, '') != ''
            AND IFNULL(`{NEW_FIELDNAME}`, '') = ''
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
