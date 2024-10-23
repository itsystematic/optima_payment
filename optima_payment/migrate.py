
import frappe
from click import secho
from optima_payment.app_setup import get_custom_fields,get_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import make_property_setter


def after_migrate():
    custom_fields = get_custom_fields()
    create_custom_fields(custom_fields, update=True)    
    add_additional_property_setter()
    update_fields_in_database()
    secho("Setup Optima Payment Setting Successfully", fg="green")



def add_additional_property_setter():
    property_setter = get_property_setter()
    for ps in property_setter:
        make_property_setter(ps)


def update_fields_in_database():
    frappe.db.sql(
        """ UPDATE `tabDocField` 
                SET options = "Cash\nBank\nCheque\nGeneral\nPhone"  
            WHERE fieldname = 'type' 
                AND parent = "Mode of Payment"
    """ , auto_commit=True)
    
    
def insert_accounting_shortcut():
    frappe.db.sql("""
        INSERT INTO `tabWorkspace Shortcut`
        (parent, parentfield, parenttype, idx, link_to, label, type, is_query_report)
        VALUES
        ('Accounting', 'shortcuts', 'Workspace', 1, 'Form/Account', 'Accounts', 'Link', 0)
    """, auto_commit=True)

# insert_accounting_shortcut()

