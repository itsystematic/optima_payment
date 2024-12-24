
import frappe
from click import secho

def after_migrate():

    update_fields_in_database()
    secho("Setup Optima Payment Setting Successfully", fg="green")



def update_fields_in_database():
    frappe.db.sql(
        """ UPDATE `tabDocField` 
                SET options = "Cash\nBank\nCheque\nGeneral\nPhone"  
            WHERE fieldname = 'type' 
                AND parent = "Mode of Payment"
    """ , auto_commit=True)
    
    
