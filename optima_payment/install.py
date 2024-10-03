from click import secho
from frappe.core.doctype.data_import.data_import import import_doc
from frappe import get_app_path

def after_install() :

    add_standard_print_format()

    secho("Data Restored Successfully" , fg="blue")

def add_standard_print_format() :
    print_format_path = get_app_path("optima_payment" , "files" , "print_format.json")
    import_doc(print_format_path)


