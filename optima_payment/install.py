import frappe
from os import listdir
from click import secho
from frappe import get_app_path
from frappe import make_property_setter
from optima_payment.app_setup import get_custom_fields,get_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.core.doctype.data_import.data_import import import_doc

def after_app_install(app_name) :

    if app_name != "optima_payment" : return    

    custom_fields = get_custom_fields()
    create_custom_fields(custom_fields, update=True)    
    add_additional_property_setter()
    #add_standard_data()

    secho("Data Restored Successfully" , fg="green")




def add_standard_data() :
    all_files_in_folders = listdir(get_app_path("optima_payment", "files"))[::-1]
    secho("Install Doctypes From Files  => {}".format(" , ".join(all_files_in_folders)), fg="blue")
    for file in all_files_in_folders:
        import_doc(get_app_path("optima_payment", "files/" + f"{file}"))

def add_additional_property_setter():
    property_setter = get_property_setter()
    for ps in property_setter:
        make_property_setter(ps)

