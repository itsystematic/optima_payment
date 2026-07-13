"""Install entrypoint for Optima Payment."""

from __future__ import annotations

import click
import frappe

from optima_payment.migration_artifact import import_cheque_legacy_artifact
from optima_payment.setup.permissions import apply_access_control, apply_hrms_access_control
from optima_payment.setup.registry import ensure_customizations, ensure_hrms_customizations
from optima_payment.setup.standard_data import add_standard_data, update_fields_in_database


def after_install() -> None:
    """Run Optima Payment setup and import any prepared legacy artifact."""
    click.secho("Starting Optima Payment installation...", fg="blue")
    add_standard_data()
    update_fields_in_database()
    ensure_customizations()
    apply_access_control()
    import_cheque_legacy_artifact()

    if "cheque" in frappe.get_installed_apps():
        click.secho(
            "Cheque is still installed on this site. The recommended flow is: "
            "export from cheque, cleanup cheque customizations, uninstall cheque, then install optima_payment.",
            fg="yellow",
        )
        
    click.secho("Thank you for installing Optima Payment!", fg="green")


def after_app_install(app_name: str) -> None:
    """Set up the optional HRMS integration when HRMS is installed after this app.

    Frappe fires this hook for every app installed on the site, passing its name —
    install-time setup already covers the HRMS-first ordering, so only react to HRMS.
    """
    if app_name != "hrms":
        return

    click.secho("HRMS installed — applying Optima Payment HRMS integration...", fg="blue")
    ensure_hrms_customizations()
    apply_hrms_access_control()
