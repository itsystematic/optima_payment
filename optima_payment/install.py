from click import secho
from frappe.core.doctype.data_import.data_import import import_doc
from frappe import get_app_path
from os import listdir

def after_app_install(app_name) :

    if app_name != "optima_payment" : return    

    add_standard_data()

    secho("Data Restored Successfully" , fg="green")




def add_standard_data() :
    all_files_in_folders = listdir(get_app_path("optima_payment", "files"))[::-1]
    secho("Install Doctypes From Files  => {}".format(" , ".join(all_files_in_folders)), fg="blue")
    for file in all_files_in_folders:
        import_doc(get_app_path("optima_payment", "files/" + f"{file}"))

