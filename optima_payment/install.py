import click
from optima_payment.setup import prepare_setup


def after_install() -> None:
    print("Starting Optima Payment installation...")
    prepare_setup()
    click.secho("Thank you for installing Optima Payment!", fg="green")

