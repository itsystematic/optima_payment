import frappe
from click import secho
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter
from optima_payment.setup import get_custom_fields, get_property_setter


def before_uninstall():    
    try:
        secho("Step 1: Removing custom fields...", fg="blue")
        delete_custom_fields(get_custom_fields())
        
        secho("Step 2: Removing property setters...", fg="blue") 
        delete_custom_property_setter()
        
        secho("Uninstall Optima Payment Complete Successfully", fg="green")
        
    except Exception as e:
        secho(f"Error during app uninstallation: {str(e)}", fg="red")
        frappe.log_error(f"Optima Payment uninstallation error: {str(e)}")


def after_app_uninstall(app_name):
    if app_name != "optima_payment":
        return

    before_uninstall()


def delete_custom_fields(custom_fields: dict):
    """Remove custom fields with proper error handling"""
    try:
        if not custom_fields:
            secho("No custom fields to remove", fg="yellow")
            return
            
        removed_count = 0
        for doctype, fields in custom_fields.items():
            try:
                if not fields:
                    continue
                    
                # Get fieldnames safely
                fieldnames = []
                for field in fields:
                    if isinstance(field, dict) and field.get("fieldname"):
                        fieldnames.append(field["fieldname"])
                
                if not fieldnames:
                    secho(f"No valid fieldnames found for {doctype}", fg="yellow")
                    continue
                
                # Delete custom fields for this doctype
                deleted_fields = frappe.db.sql("""
                    SELECT name FROM `tabCustom Field` 
                    WHERE fieldname IN %s AND dt = %s
                """, [fieldnames, doctype], as_dict=True)
                
                for field_record in deleted_fields:
                    try:
                        frappe.delete_doc("Custom Field", field_record.name, force=True)
                        removed_count += 1
                    except Exception as e:
                        secho(f"Error deleting custom field {field_record.name}: {str(e)}", fg="yellow")
                        continue
                
                # Clear cache for this doctype
                frappe.clear_cache(doctype=doctype)
                secho(f"Processed custom fields for {doctype}", fg="green")
                
            except Exception as e:
                secho(f"Error processing custom fields for {doctype}: {str(e)}", fg="yellow")
                frappe.log_error(f"Custom fields removal error for {doctype}: {str(e)}")
                continue
        
        secho(f"Removed {removed_count} custom fields total", fg="green")
        frappe.db.commit()
        
    except Exception as e:
        secho(f"Error in delete_custom_fields: {str(e)}", fg="red")
        frappe.log_error(f"Custom fields removal error: {str(e)}")


def delete_custom_property_setter():
    """Remove property setters with comprehensive error handling"""
    try:
        property_setters = get_property_setter()
        
        if not property_setters:
            secho("No property setters to remove", fg="yellow")
            return
            
        removed_count = 0
        for item in property_setters:
            try:
                # Validate the item structure
                if not item or not isinstance(item, dict):
                    secho(f"Skipping invalid property setter item: {item}", fg="yellow")
                    continue
                
                # Check for required keys with proper error handling
                doctype = item.get("doctype")
                property_name = item.get("property") 
                field_name = item.get("fieldname")
                
                if not doctype:
                    secho(f"Skipping property setter with missing doctype: {item}", fg="yellow")
                    continue
                    
                if not property_name:
                    secho(f"Skipping property setter with missing property: {item}", fg="yellow")
                    continue
                
                # Call the delete function with validated parameters
                if delete_property_setter_safe(doctype, property_name, field_name):
                    removed_count += 1
                    secho(f"Removed property setter: {doctype}-{field_name or 'DocType'}-{property_name}", fg="green")
                    
            except Exception as e:
                secho(f"Error processing property setter {item}: {str(e)}", fg="yellow")
                frappe.log_error(f"Property setter removal error: {str(e)}")
                continue
        
        secho(f"Removed {removed_count} property setters total", fg="green")
        frappe.db.commit()
        
    except Exception as e:
        secho(f"Error in delete_custom_property_setter: {str(e)}", fg="red")
        frappe.log_error(f"Property setter removal error: {str(e)}")


def delete_property_setter_safe(doctype, property_name, field_name=None):
    """Delete a specific property setter with error handling"""
    try:
        # Build the filter for finding the property setter
        filters = {
            "doc_type": doctype,
            "property": property_name
        }
        
        # Add field_name to filter if provided
        if field_name:
            filters["field_name"] = field_name
        
        # Find existing property setter
        existing_ps = frappe.db.exists("Property Setter", filters)
        
        if existing_ps:
            frappe.delete_doc("Property Setter", existing_ps, force=True)
            return True
        else:
            secho(f"Property setter not found: {doctype}-{field_name or 'DocType'}-{property_name}", fg="yellow")
            return False
            
    except Exception as e:
        secho(f"Error deleting property setter {doctype}-{field_name}-{property_name}: {str(e)}", fg="red")
        frappe.log_error(f"Individual property setter deletion error: {str(e)}")
        return False

# import frappe
# from click import secho
# from frappe.custom.doctype.property_setter.property_setter import delete_property_setter
# from optima_payment.app_setup import (get_custom_fields,get_property_setter)


# def after_app_uninstall(app_name):

#     if app_name != "optima_payment" : return

#     delete_custom_fields(get_custom_fields())
#     delete_custom_property_setter()
#     secho("Uninstall Optima Payment Complete Successfully", fg="green")


# def delete_custom_fields(custom_fields: dict):
#     for doctype, fields in custom_fields.items():
#         frappe.db.delete(
#             "Custom Field",
#             {
#                 "fieldname": ("in", [field["fieldname"] for field in fields]),
#                 "dt": doctype,
#             },
#         )
#         frappe.clear_cache(doctype=doctype)


# def delete_custom_property_setter():
#     property_setter = get_property_setter()
    
#     for item in property_setter:
#         field_name = item.get("fieldname", None)
#         delete_property_setter(item["doctype"], item["property"], field_name)
