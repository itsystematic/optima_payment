
from click import secho
from optima_payment.setup import update_fields_in_database

def after_migrate():

    update_fields_in_database()
    secho("Updated Optima Payment field options successfully", fg="green")
