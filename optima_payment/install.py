import click
from optima_payment.setup import prepare_setup


def after_install() -> None:
    try:
        print("Starting Optima Payment installation...")
        prepare_setup()

        click.secho("Thank you for installing Optima Payment!", fg="green")
        
    except Exception as e:
        # Don't raise the error to prevent installation failure
        click.secho("Installation completed with warnings. Check error log for details.", fg="yellow")
        click.secho(f"Error during app installation: {str(e)}", fg="red")


