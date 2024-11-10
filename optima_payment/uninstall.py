
import frappe
from click import secho
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter
from optima_payment.app_setup import (get_custom_fields,get_property_setter)


def after_app_uninstall(app_name):

    if app_name != "optima_payment" : return

    delete_custom_fields(get_custom_fields())
    delete_custom_property_setter()
    secho("Uninstall Optima Payment Complete Successfully", fg="green")


def delete_custom_fields(custom_fields: dict):
    for doctype, fields in custom_fields.items():
        frappe.db.delete(
            "Custom Field",
            {
                "fieldname": ("in", [field["fieldname"] for field in fields]),
                "dt": doctype,
            },
        )
        frappe.clear_cache(doctype=doctype)


def delete_custom_property_setter():
    property_setter = get_property_setter()
    
    for item in property_setter:
        field_name = item.get("fieldname", None)
        delete_property_setter(item["doctype"], item["property"], field_name)
