"""Fix the misspelled 'Optima Payment Manger' role to 'Optima Payment Manager'.

Installed sites imported the role from the retired files/role.json under the misspelled name.
Renaming the Role updates its link references (Has Role assignments, Custom DocPerm.role), so
existing users and permissions follow. Fresh installs get the correct name from
setup/permissions.py and never hit this patch.
"""

import click
import frappe

OLD_NAME = "Optima Payment Manger"
NEW_NAME = "Optima Payment Manager"


def execute() -> None:
    if not frappe.db.exists("Role", OLD_NAME):
        click.secho(f"Role '{OLD_NAME}' not found; nothing to rename", fg="yellow")
        return

    if frappe.db.exists("Role", NEW_NAME):
        # Both exist (e.g. a partial prior run): drop the misspelled one so the correct
        # role created from code remains the single source of truth.
        frappe.delete_doc("Role", OLD_NAME, force=True)
        click.secho(f"Removed leftover misspelled role '{OLD_NAME}'", fg="green")
        return

    frappe.rename_doc("Role", OLD_NAME, NEW_NAME, force=True)
    click.secho(f"Renamed role '{OLD_NAME}' -> '{NEW_NAME}'", fg="green")
