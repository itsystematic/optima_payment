"""Shared install-time data and stable metadata updates for Optima Payment.

Print formats are seeded here as a one-time ``import_doc`` at install: 75 KB of opaque bank
HTML belongs in data, not Python, and is deliberately not reversed on uninstall so per-site
edits survive. Roles and their Custom DocPerms are NOT seeded here anymore — they moved to
code in ``setup/permissions.py`` (reversible on uninstall). See ``docs/setup/permissions.md``.
"""

from __future__ import annotations

import click
import frappe
from frappe import get_app_path
from frappe.core.doctype.data_import.data_import import import_doc

STANDARD_DATA_FILES = [
    "print_format.json",
]


def add_standard_data() -> None:
    """Import standard data files (print formats) required by Optima Payment."""
    files_path = get_app_path("optima_payment", "files")
    if not frappe.os.path.exists(files_path):
        click.secho("Files directory not found, skipping data import", fg="yellow")
        return

    click.secho(
        "Install DocTypes From Files => {}".format(", ".join(STANDARD_DATA_FILES)),
        fg="blue",
    )

    for file in STANDARD_DATA_FILES:
        file_path = get_app_path("optima_payment", f"files/{file}")
        
        if not frappe.os.path.exists(file_path):
            click.secho(f"Skipping missing file: {file}", fg="yellow")
            continue
        
        import_doc(file_path)
        click.secho(f"Successfully imported: {file}", fg="green")


def update_fields_in_database() -> None:
    """Keep standard field options aligned with Optima Payment expectations."""
    add_cheque_and_letter_of_credit_type()

def add_cheque_and_letter_of_credit_type() -> None:
    """Add 'Cheque' and 'Letter of Credit' as new options to the 'Payment Type' field in the 'Payment Entry' DocType."""
    frappe.db.sql(
        """ UPDATE `tabDocField`
                SET options = "Cash\nBank\nCheque\nGeneral\nPhone\nLetter of Credit"
            WHERE fieldname = 'type'
                AND parent = "Mode of Payment"
    """,
        auto_commit=True,
    )