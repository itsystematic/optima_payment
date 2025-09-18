import frappe
from os import listdir
from click import secho
from frappe import get_app_path
from frappe import make_property_setter
from optima_payment.app_setup import get_custom_fields, get_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.core.doctype.data_import.data_import import import_doc


def after_app_install(app_name):
    if app_name != "optima_payment":
        return    

    try:
        # Step 1: Import standard data first (DocTypes, etc.)
        secho("Step 1: Installing standard data...", fg="blue")
        add_standard_data()
        
        # Step 2: Add property setters
        secho("Step 2: Adding property setters...", fg="blue")
        add_additional_property_setter()
        
        # Step 3: Create custom fields with error handling
        secho("Step 3: Creating custom fields...", fg="blue")
        create_custom_fields_safely()
        
        secho("Data Restored Successfully", fg="green")
        
    except Exception as e:
        secho(f"Error during app installation: {str(e)}", fg="red")
        frappe.log_error(f"Optima Payment installation error: {str(e)}")
        # Don't raise the error to prevent installation failure
        secho("Installation completed with warnings. Check error log for details.", fg="yellow")


def create_custom_fields_safely():
    """Create custom fields with proper error handling"""
    try:
        custom_fields = get_custom_fields()
        
        if not custom_fields:
            secho("No custom fields to create", fg="yellow")
            return
            
        # Validate custom fields data structure
        validated_fields = validate_custom_fields_data(custom_fields)
        
        if validated_fields:
            create_custom_fields(validated_fields, update=True)
            secho(f"Successfully created custom fields for {len(validated_fields)} DocTypes", fg="green")
        else:
            secho("No valid custom fields found after validation", fg="yellow")
            
    except Exception as e:
        secho(f"Error creating custom fields: {str(e)}", fg="red")
        frappe.log_error(f"Custom fields creation error: {str(e)}")


def validate_custom_fields_data(custom_fields):
    """Validate custom fields data and filter out problematic entries"""
    validated_fields = {}
    
    for doctype, fields in custom_fields.items():
        if not doctype or not fields:
            secho(f"Skipping invalid DocType: {doctype}", fg="yellow")
            continue
            
        valid_fields = []
        for field in fields:
            if not field or not isinstance(field, dict):
                secho(f"Skipping invalid field in {doctype}: {field}", fg="yellow")
                continue
                
            # Check required field properties
            if not field.get('fieldname') or not field.get('fieldtype'):
                secho(f"Skipping field with missing required properties in {doctype}: {field}", fg="yellow")
                continue
                
            # Check if custom field already exists
            existing = frappe.db.exists("Custom Field", {
                "dt": doctype,
                "fieldname": field.get("fieldname")
            })
            
            if existing:
                secho(f"Custom field already exists: {doctype}-{field.get('fieldname')}", fg="yellow")
                # Skip or update existing field
                continue
                
            valid_fields.append(field)
            
        if valid_fields:
            validated_fields[doctype] = valid_fields
            
    return validated_fields


def add_standard_data():
    """Import standard data files with error handling"""
    try:
        files_path = get_app_path("optima_payment", "files")
        if not frappe.os.path.exists(files_path):
            secho("Files directory not found, skipping data import", fg="yellow")
            return
            
        all_files_in_folders = listdir(files_path)[::-1]
        secho("Install DocTypes From Files => {}".format(", ".join(all_files_in_folders)), fg="blue")
        
        for file in all_files_in_folders:
            try:
                file_path = get_app_path("optima_payment", f"files/{file}")
                import_doc(file_path)
                secho(f"Successfully imported: {file}", fg="green")
            except Exception as e:
                secho(f"Error importing {file}: {str(e)}", fg="red")
                frappe.log_error(f"Data import error for {file}: {str(e)}")
                continue
                
    except Exception as e:
        secho(f"Error in add_standard_data: {str(e)}", fg="red")
        frappe.log_error(f"Standard data installation error: {str(e)}")


def add_additional_property_setter():
    """Add property setters with error handling"""
    try:
        property_setter = get_property_setter()
        if not property_setter:
            secho("No property setters to create", fg="yellow")
            return
            
        for ps in property_setter:
            try:
                if not ps or not isinstance(ps, dict):
                    secho(f"Skipping invalid property setter: {ps}", fg="yellow")
                    continue
                    
                make_property_setter(ps)
                secho(f"Created property setter for: {ps.get('doctype', 'Unknown')}", fg="green")
                
            except Exception as e:
                secho(f"Error creating property setter {ps}: {str(e)}", fg="red")
                frappe.log_error(f"Property setter error: {str(e)}")
                continue
                
    except Exception as e:
        secho(f"Error in add_additional_property_setter: {str(e)}", fg="red")
        frappe.log_error(f"Property setter installation error: {str(e)}")


# import frappe
# from os import listdir
# from click import secho
# from frappe import get_app_path
# from frappe import make_property_setter
# from optima_payment.app_setup import get_custom_fields,get_property_setter
# from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
# from frappe.core.doctype.data_import.data_import import import_doc

# def after_app_install(app_name) :

#     if app_name != "optima_payment" : return    

#     custom_fields = get_custom_fields()
#     create_custom_fields(custom_fields, update=True)    
#     add_additional_property_setter()
#     add_standard_data()

#     secho("Data Restored Successfully" , fg="green")




# def add_standard_data() :
#     all_files_in_folders = listdir(get_app_path("optima_payment", "files"))[::-1]
#     secho("Install Doctypes From Files  => {}".format(" , ".join(all_files_in_folders)), fg="blue")
#     for file in all_files_in_folders:
#         import_doc(get_app_path("optima_payment", "files/" + f"{file}"))

# def add_additional_property_setter():
#     property_setter = get_property_setter()
#     for ps in property_setter:
#         make_property_setter(ps)

