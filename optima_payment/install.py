import click
import frappe
from optima_payment.migration_artifact import import_cheque_legacy_artifact
from optima_payment.setup import prepare_setup


def after_install() -> None:
    print("Starting Optima Payment installation...")
    prepare_setup()
    import_cheque_legacy_artifact()
    if "cheque" in frappe.get_installed_apps():
        click.secho(
            "Cheque is still installed on this site. The recommended flow is: "
            "export from cheque, cleanup cheque customizations, uninstall cheque, then install optima_payment.",
            fg="yellow",
        )
    click.secho("Thank you for installing Optima Payment!", fg="green")
