"""Shared install-time data and stable metadata updates for Optima Payment."""

from __future__ import annotations

from os import listdir

import click
import frappe
from frappe import get_app_path
from frappe.core.doctype.data_import.data_import import import_doc


def add_standard_data() -> None:
    """Import standard data files required by Optima Payment."""
    files_path = get_app_path("optima_payment", "files")
    if not frappe.os.path.exists(files_path):
        click.secho("Files directory not found, skipping data import", fg="yellow")
        return

    all_files_in_folders = listdir(files_path)[::-1]
    click.secho(
        "Install DocTypes From Files => {}".format(", ".join(all_files_in_folders)),
        fg="blue",
    )

    for file in all_files_in_folders:
        file_path = get_app_path("optima_payment", f"files/{file}")
        import_doc(file_path)
        click.secho(f"Successfully imported: {file}", fg="green")


def update_fields_in_database() -> None:
    """Keep standard field options aligned with Optima Payment expectations."""
    frappe.db.sql(
        """ UPDATE `tabDocField`
                SET options = "Cash\nBank\nCheque\nGeneral\nPhone"
            WHERE fieldname = 'type'
                AND parent = "Mode of Payment"
    """,
        auto_commit=True,
    )
