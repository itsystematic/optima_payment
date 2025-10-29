import frappe
from frappe import get_app_path
from frappe import make_property_setter
from frappe.core.doctype.data_import.data_import import import_doc
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

import json
import click
from os import listdir

from optima_payment import if_hrms_app_installed
from optima_payment.setup import get_custom_fields, get_property_setter

MAIN_ORDER_FIELDS = [
    "type_of_payment",
    "naming_series",
    "payment_type",
    "payment_order_status",
    "multi_expense",
    "column_break_5",
    "posting_date",
    "company",
    "mode_of_payment",
    "cheque_deposit_slip",
    "is_endorsed_cheque",
    "receivable_cheque",
    "company_expenses",
    "company_expense",
    "total_amount",
    "party_section",
    "party_type",
    "party",
    "party_name",
    "book_advance_payments_in_separate_party_account",
    "reconcile_on_advance_payment_date",
    "column_break_11",
    "bank_account",
    "party_bank_account",
    "contact_person",
    "contact_email",
    "transaction_references",
    "reference_no",
    "payee_name",
    "column_break_23",
    "reference_date",
    "bank_name",
    "clearance_date",
    "payment_accounts_section",
    "party_balance",
    "paid_from",
    "paid_from_account_type",
    "paid_from_account_currency",
    "paid_from_account_balance",
    "column_break_18",
    "paid_to",
    "paid_to_account_type",
    "paid_to_account_currency",
    "paid_to_account_balance",
    "payment_amounts_section",
    "paid_amount",
    "paid_amount_after_tax",
    "source_exchange_rate",
    "base_paid_amount",
    "base_paid_amount_after_tax",
    "column_break_21",
    "received_amount",
    "received_amount_after_tax",
    "target_exchange_rate",
    "base_received_amount",
    "base_received_amount_after_tax",
    "section_break_14",
    "get_outstanding_invoices",
    "get_outstanding_orders",
    "references",
    "section_break_34",
    "total_allocated_amount",
    "base_total_allocated_amount",
    "set_exchange_gain_loss",
    "column_break_36",
    "unallocated_amount",
    "difference_amount",
    "write_off_difference_amount",
    "taxes_and_charges_section",
    "purchase_taxes_and_charges_template",
    "sales_taxes_and_charges_template",
    "column_break_55",
    "apply_tax_withholding_amount",
    "tax_withholding_category",
    "section_break_56",
    "taxes",
    "section_break_60",
    "base_total_taxes_and_charges",
    "column_break_61",
    "total_taxes_and_charges",
    "deductions_or_loss_section",
    "deductions",
    "cheque_details",
    "cheque_status",
    "pay_mode_of_payment",
    "bank_fees_amount",
    "accounting_dimensions_section",
    "project",
    "dimension_col_break",
    "cost_center",
    "section_break_12",
    "status",
    "custom_remarks",
    "remarks",
    "base_in_words",
    "is_opening",
    "column_break_16",
    "letter_head",
    "print_heading",
    "bank",
    "bank_account_no",
    "payment_order",
    "in_words",
    "subscription_section",
    "auto_repeat",
    "amended_from",
    "title",
]

BANK_GUARANTEE_FIELDS_ORDER = [
    "recent_transaction_date",
    "bank_guarantee_purpose",
    "bg_type",
    "reference_doctype",
    "reference_docname",
    "customer",
    "supplier",
    "project",
    "company",
    "cost_center",
    "conditions",
    "guarantee_type",
    "column_break_6",
    "posting_date",
    "bank_guarantee_status",
    "net_amount",
    "tax_amount",
    "amount",
    "bank_guarantee_percent",
    "bank_guarantee_amount",
    "returned_date",
    "start_date",
    "validity",
    "end_date",
    "extend_validity",
    "no_of_extended_days",
    "new_end_date",
    "bank_account_info",
    "bank",
    "account",
    "bank_account_no",
    "issue_commission",
    "issue_commission_amount",
    "bank_rate_",
    "bank_amount",
    "cheque_no",
    "cheque_date",
    "column_break_17",
    "bank_account",
    "bank_guarantee_account",
    "iban",
    "branch_code",
    "swift_number",
    "banking_facilities",
    "bank_facilities_account",
    "facilities_rate_",
    "facility_amount",
    "section_break_14",
    "name_of_beneficiary",
    "charges",
    "fixed_deposit_number",
    "margin_money",
    "column_break_19",
    "bank_guarantee_number",
    "remarks",
    "amended_from",
    "custom_section_break_sluyu",
    "more_information"
]



def prepare_setup() -> None:
    """ Function To Setting up Optima Payment Customizations """
    # Step 1: Import standard data first (DocTypes, etc.)
    click.secho("Step 1: Installing standard data...", fg="blue")
    add_standard_data()
    
    # Step 2: Add property setters
    click.secho("Step 2: Adding property setters...", fg="blue")
    add_additional_property_setter()
    
    # Step 3: Create custom fields with error handling
    click.secho("Step 3: Creating custom fields...", fg="blue")
    create_custom_fields_safely()
    
    click.secho("Data Restored Successfully", fg="green")




def create_custom_fields_safely():
    """Create custom fields with proper error handling"""
    try:
        custom_fields = get_custom_fields()
        
        if not custom_fields:
            click.secho("No custom fields to create", fg="yellow")
            return
            
        # Validate custom fields data structure
        validated_fields = validate_custom_fields_data(custom_fields)
        
        if validated_fields:
            create_custom_fields(validated_fields, update=True)
            click.secho(f"Successfully created custom fields for {len(validated_fields)} DocTypes", fg="green")
        else:
            click.secho("No valid custom fields found after validation", fg="yellow")
            
    except Exception as e:
        click.secho(f"Error creating custom fields: {str(e)}", fg="red")
        frappe.log_error(f"Custom fields creation error: {str(e)}")


def validate_custom_fields_data(custom_fields):
    """Validate custom fields data and filter out problematic entries"""
    validated_fields = {}
    
    for doctype, fields in custom_fields.items():
        if not doctype or not fields:
            click.secho(f"Skipping invalid DocType: {doctype}", fg="yellow")
            continue
            
        valid_fields = []
        for field in fields:
            if not field or not isinstance(field, dict):
                click.secho(f"Skipping invalid field in {doctype}: {field}", fg="yellow")
                continue
                
            # Check required field properties
            if not field.get('fieldname') or not field.get('fieldtype'):
                click.secho(f"Skipping field with missing required properties in {doctype}: {field}", fg="yellow")
                continue
                
            # Check if custom field already exists
            existing = frappe.db.exists("Custom Field", {
                "dt": doctype,
                "fieldname": field.get("fieldname")
            })
            
            if existing:
                click.secho(f"Custom field already exists: {doctype}-{field.get('fieldname')}", fg="yellow")
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
            click.secho("Files directory not found, skipping data import", fg="yellow")
            return
            
        all_files_in_folders = listdir(files_path)[::-1]
        click.secho("Install DocTypes From Files => {}".format(", ".join(all_files_in_folders)), fg="blue")
        
        for file in all_files_in_folders:
            try:
                file_path = get_app_path("optima_payment", f"files/{file}")
                import_doc(file_path)
                click.secho(f"Successfully imported: {file}", fg="green")
            except Exception as e:
                click.secho(f"Error importing {file}: {str(e)}", fg="red")
                frappe.log_error(f"Data import error for {file}: {str(e)}")
                continue
                
    except Exception as e:
        click.secho(f"Error in add_standard_data: {str(e)}", fg="red")
        frappe.log_error(f"Standard data installation error: {str(e)}")


def add_additional_property_setter():
    """Add property setters with error handling"""
    try:
        property_setter = get_property_setter()
        if not property_setter:
            click.secho("No property setters to create", fg="yellow")
            return
            
        for ps in property_setter:
            try:
                if not ps or not isinstance(ps, dict):
                    click.secho(f"Skipping invalid property setter: {ps}", fg="yellow")
                    continue
                    
                make_property_setter(ps)
                click.secho(f"Created property setter for: {ps.get('doctype', 'Unknown')}", fg="green")
                
            except Exception as e:
                click.secho(f"Error creating property setter {ps}: {str(e)}", fg="red")
                frappe.log_error(f"Property setter error: {str(e)}")
                continue
                
    except Exception as e:
        click.secho(f"Error in add_additional_property_setter: {str(e)}", fg="red")
        frappe.log_error(f"Property setter installation error: {str(e)}")


def get_custom_fields() -> dict[str, list[dict]]:
    """Return custom fields related to Optima Payment to be created in the system"""
    custom_fields = {
        "Mode of Payment": [
            {
                "fieldname": "is_payable_cheque",
                "fieldtype": "Check",
                "insert_after": "accounts",
                "label": "Is Payable Cheque",
                "default": 0,
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_receivable_cheque == 0 ;",
            },
            {
                "fieldname": "is_receivable_cheque",
                "fieldtype": "Check",
                "insert_after": "is_payable_cheque",
                "label": "Is Receivable Cheque",
                "default": 0,
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_payable_cheque == 0 ;",
            },
            {
                "fieldname": "cheque_collection_fee",
                "fieldtype": "Float",
                "label": "Cheque Collection Fee",
                "insert_after": "type",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
            {
                "fieldname": "cheque_rejection_fee",
                "fieldtype": "Float",
                "label": "Cheque Rejection Fee",
                "insert_after": "cheque_collection_fee",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
        ],
        "Payment Entry": [
            {
                "fieldname": "payee_name",
                "fieldtype": "Data",
                "insert_after": "reference_no",
                "label": "Payee Name",
                "no_copy": 0,
                "hidden": 0,
            },
            {
                "fieldname": "cheque_deposit_slip",
                "fieldtype": "Link",
                "label": "Cheque Deposit Slip",
                "options": "Cheque Deposit Slip",
                "insert_after": "mode_of_payment",
                "read_only": 1,
            },
            {
                "fieldname": "bank_name",
                "fieldtype": "Link",
                "insert_after": "reference_date",
                "label": "Bank Name",
                "options": "Bank",
                "no_copy": 0,
                "hidden": 0,
            },
            {
                "fieldname": "cheque_details",
                "fieldtype": "Section Break",
                "insert_after": "clearance_date",
                "label": "Cheque Details",
                "depends_on": "eval: doc.mode_of_payment == 'Receivable Cheque' || doc.mode_of_payment == 'Payable Cheque'",
            },
            {
                "fieldname": "cheque_status",
                "fieldtype": "Select",
                "options": "\nEncashment\nCollected\nIssuance\nFor Collection\nDeposited\nDeposit Under Collection\nRejected\nReturn To Holder\nEndorsed\nIssuance From Endorsed\nCancelled\nReturned",
                "insert_after": "cheque_details",
                "label": "Cheque Status",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "bank_fees_amount",
                "fieldtype": "Currency",
                "insert_after": "cheque_status",
                "label": "Bank Fees Amount",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "multi_expense",
                "fieldtype": "Check",
                "label": "Multi Expense",
                "insert_after": "payment_order_status",
                "depends_on": 'eval: doc.payment_type === "Pay" && doc.is_endorsed_cheque !== 1 ',
            },
            {
                "fieldname": "is_endorsed_cheque",
                "fieldtype": "Check",
                "label": "Is Endorsed Cheque",
                "insert_after": "mode_of_payment",
                "depends_on": "eval: doc.payment_type == 'Pay'",
                "default": 0,
            },
            {
                "fieldname": "receivable_cheque",
                "fieldtype": "Link",
                "options": "Payment Entry",
                "label": "Receivable Cheque",
                "insert_after": "is_endorsed_cheque",
                "depends_on": "eval: doc.is_endorsed_cheque == 1 && doc.payment_type == 'Pay'; ",
                "mandatory_depends_on": "eval: doc.is_endorsed_cheque == 1 && doc.payment_type == 'Pay'; ",
            },
            {
                "label": "Company Expenses",
                "fieldname": "company_expenses",
                "fieldtype": "Section Break",
                # "insert_after": "bank_fees_amount",
                "insert_after": "receivable_cheque",
                "depends_on": "eval: doc.multi_expense == 1",
            },
            {
                "fieldname": "company_expense",
                "fieldtype": "Table",
                "label": "Company Expense",
                "options": "Company Expense Details",
                "insert_after": "company_expenses",
            },
            {
                "fieldname": "total_amount",
                "fieldtype": "Float",
                "label": "Total Amount",
                "insert_after": "company_expense",
                "read_only": 1,
                #  "precision": "",
            },
        ],

        "Bank": [
            {
                "label": "Print Formats",
                "fieldname": "bank_formats",
                "fieldtype": "Section Break",
                "insert_after": "data_import_configuration_section",
            },
            {
                "fieldname": "bank_print_format",
                "fieldtype": "Table",
                "label": "Bank Print Format",
                "options": "Bank Print Format Items",
                "insert_after": "bank_formats",
            },
            # Bank Guarantee Related Fields
            {
                "fieldname": "company",
                "label": "Company",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "website" 
            },
        ],
        "Letter Head": [
            {
                "fieldname": "is_box",
                "fieldtype": "Check",
                "label": "Box",
                "insert_after": "is_default",
            },
            # Bank Guarantee Related Fields
            {
                "fieldname": "customer",
                "fielndtype": "Link",
                "label": "Customer",
                "insert_after": "reference_docname",
                "options": "Customer",
                "depends_on": 'eval: doc.reference_doctype == "Sales Order"',
            },
            {
                "fieldname": "supplier",
                "fielndtype": "Link",
                "label": "Supplier",
                "insert_after": "customer",
                "options": "Supplier",
                "depends_on": 'eval: doc.reference_doctype == "Purchase Invoice"',
            },
        ],
        "Bank Account": [
            # Bank Guarantee Related Fields
            {
                "fieldname": "bank_guarantee_account",
                "fieldtype": "Link",
                "label": "Bank Guarantee Account",
                "insert_after": "company",
                "options": "Account",
            },
        ],
        "Company": [
            # Bank Guarantee Related Fields
            {
                "fieldname": "default_insurance_account",
                "fieldtype": "Link",
                "label": "Default Insurance Account",
                "options": "Account",
                "insert_after": "default_bank_account",
            },
            {
                "fieldname": "default_receiving_insurance_account",
                "fieldtype": "Link",
                "label": "Default Receiving Insurance Account",
                "options": "Account",
                "insert_after": "default_insurance_account",
            },
            {
                "fieldname": "bank_fees_account",
                "fieldtype": "Link",
                "label": "Bank Fees Account",
                "options": "Account",
                "insert_after": "default_receiving_insurance_account",
            },
            {
                "fieldname": "lost_expense_Bank_guarantee_account",
                "fieldtype": "Link",
                "label": "Lost Expense Bank Guarantee Account",
                "options": "Account",
                "insert_after": "bank_fees_account",
            },
        ],
        "GL Entry": [
            # Bank Guarantee Related Fields
            {
                "fieldname": "is_bank_guarantee_comission_entry",
                "fieldtype": "Check",
                "label": "Bank Guarantee Comission Entry",
                "insert_after": "transaction_exchange_rate",
                "default": 0,
                "hidden": 1
            }
        ],
        "Bank Guarantee": [
            {
                "fieldname": "bank_guarantee_percent",
                "fieldtype": "Percent",
                "label": "Bank Guarantee Percent",
                "reqd": 1,
                "precision": 0
            },
            {
                "fieldname": "bank_guarantee_amount",
                "fieldtype": "Currency",
                "label": "Bank Guarantee Amount",
                "reqd": 1,
                "no_copy":1,
                "read_only": 1,
                "depends_on": "eval: doc.bank_guarantee_percent != 0",
            },
            {
                "fieldname": "custom_section_break_sluyu",
                "fieldtype": "Section Break",
            },
            {
                "fieldname": "tax_amount",
                "fieldtype": "Currency",
                "label": "Tax Amount",
                "insert_after": "Net Amount",
                "read_only": 1,
            },
            {
                "fieldname": "net_amount",
                "fieldtype": "Currency",
                "label": "Net Amount",
                "insert_after": "Bank Guarantee Status",
                "read_only": 1,
            },
            {
                "fieldname": "cost_center",
                "fieldtype": "Link",
                "label": "Cost Center",
                "insert_after": "project",
                "options": "Cost Center",
            },
            {
                "fieldname": "bank_guarantee_account",
                "fieldtype": "Link",
                "label": "Bank Guarantee Account",
                "insert_after": "Bank Account",
                "options": "Account",
                "read_only": 1,
            },
            {
                "fieldname": "returned_date",
                "fieldtype": "Date",
                "label": "Returned Date",
                "insert_after": "Grand Amount",
                "read_only": 1,
            },
            {
                "fieldname": "returned_date",
                "fieldtype": "Date",
                "label": "Returned Date",
                "insert_after": "Grand Amount",
                "read_only": 1,
            },
            {
                "fieldname": "section_break_123",
                "fieldtype": "Section Break",
                "label": "",
                "insert_after": "Bank Guarantee",
            },
            {
                "fieldname": "column_break_1230",
                "fieldtype": "Column Break",
                "label": "",
                "insert_after": "Other Details",
            },
            {
                "fieldname": "company",
                "fieldtype": "Link",
                "label": "Company",
                "insert_after": "Project",
                "options": "Company",
                "read_only": 1,
                "hidden": 1,
            },
            {
                "fieldname": "cheque_date",
                "fieldtype": "Date",
                "label": "Cheque Date",
                "insert_after": "Cheque No",
                "depends_on": "eval: doc.bank_guarantee_purpose == 'Cheque'"
            },
            {
                "fieldname": "cheque_no",
                "fieldtype": "Data",
                "label": "Cheque No",
                "insert_after": "Bank Amount",
                "depends_on": "eval: doc.bank_guarantee_purpose == 'Cheque'",
            },
            {
                "fieldname": "new_end_date",
                "fieldtype": "Date",
                "label": "New End Date",
                "insert_after": "No of Extended Days",
                "read_only": 1,
                "allow_on_submit": 1,
                "depends_on": "eval: doc.extend_validity == 1",
            },
            {
                "fieldname": "no_of_extended_days",
                "fieldtype": "Int",
                "label": "No of Extended Days",
                "insert_after": "Extend Validity",
                "depends_on": "eval:doc.extend_validity == 1"
            },
            {
                "fieldname": "extend_validity",
                "fieldtype": "Check",
                "label": "Extend Validity",
                "insert_after": "End Date",
                "depends_on": "eval: doc.bank_guarantee_status == 'Extended'",
            },
            {
                "fieldname": "posting_date",
                "fieldtype": "Date",
                "label": "Posting Date",
                "insert_after": "column_break_6",
                "default": "Today",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "bank_guarantee_status",
                "fieldtype": "Select",
                "label": "Bank Guarantee Status",
                "insert_after": "Posting Date",
                "options": "New\nExists\nIssued\nReturned\nExpired\nExtended\nLost",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "bank_facilities_account",
                "fieldtype": "Link",
                "label": "Bank Facilities Account",
                "insert_after": "Banking Facilities",
                "options": "Bank Account",
                "depends_on": "eval: doc.banking_facilities == 'With Facilities'",
            },
            {
                "fieldname": "facility_amount",
                "fieldtype": "Float",
                "label": "Facility Amount",
                "insert_after": "Facilities Rate (%)",
                "depends_on": 'eval:doc.banking_facilities == "With Facilities"',
            },
            {
                "fieldname": "facilities_rate_",
                "fieldtype": "Percent",
                "label": "Facilities Rate (%)",
                "insert_after": "Bank Facilities Account",
                "depends_on": 'eval:doc.banking_facilities == "With Facilities"',
            },
            {
                "fieldname": "banking_facilities",
                "fieldtype": "Select",
                "label": "Banking Facilities",
                "insert_after": "SWIFT number",
                "depends_on": 'eval:doc.bank_guarantee_purpose == "Bank Guarantee"',
                "options": "Without Facilities\nWith Facilities",
            },
            {
                "fieldname": "bank_amount",
                "fieldtype": "Float",
                "label": "Bank Amount",
                "insert_after": "Bank Rate (%)",
            },
            {
                "fieldname": "bank_rate_",
                "fieldtype": "Percent",
                "label": "Bank Rate (%)",
                "insert_after": "Issue Commission Amount",
                "default": 100,
                "read_only_depends_on": "eval: doc.banking_facilities == 'Without Facilities'",
            },
            {
                "fieldname": "issue_commission_amount",
                "fieldtype": "Float",
                "label": "Issue Commission Amount",
                "insert_after": "Issue Commission",
                "depends_on": "eval:doc.issue_commission == 1",
                "default": 0
            },
            {
                "fieldname": "issue_commission",
                "fieldtype": "Check",
                "label": "Issue Commission",
                "insert_after": "Bank Account No",
                "depends_on": 'eval:doc.bg_type=="Providing"',
            },
            {
                "fieldname": "guarantee_type",
                "fieldtype": "Select",
                "label": "Guarantee Type",
                "insert_after": "Conditions",
                "options": "\nInitial\nAdvanced Paymnet\nFinal\nFinacial",
                "reqd": 1,
            },
            {
                "fieldname": "conditions",
                "fieldtype": "Select",
                "label": "Conditions",
                "insert_after": "New End Date",
                "options": "\nWith Condition\nWithout Condition",
            },
            {
                "fieldname": "bank_guarantee_purpose",
                "fieldtype": "Select",
                "label": "Bank Guarantee Purpose",
                "insert_after": "",
                "options": "\nBank Guarantee\nCheque\nCash\nDeduction",
                "default": "Bank Guarantee",
                "read_only": 1,
                "hidden": 1

            },
            {
                "fieldname": "bank_guarantee_percent",
                "fieldtype": "Percent",
                "label": "Bank Guarantee Percent",
            },
            {
                "fieldname": "remarks",
                "fieldtype": "Small Text",
                "label": "Remarks",
                "print_hide": 1
            },
            {
                "fieldname": "recent_transaction_date",
                "fieldtype": "Date",
                "hidden": 1
            }
        ],
    }

    add_hrms_fields(custom_fields)

    return custom_fields


@if_hrms_app_installed
def add_hrms_fields(custom_fields: dict) -> None:
    """
    Add custom fields to "Expense Claim Detail" doctype if HRMS app is installed.

    Args:
        custom_fields (dict): Dictionary of custom fields.
    """
    custom_fields["Expense Claim Detail"] = [
        {
            "fieldname": "purchase_invoice",
            "fieldtype": "Link",
            "label": "Purchase Invoice",
            "options": "Purchase Invoice",
        }
    ]


def get_property_setter():

    property_setter = [
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "reference_no",
            "property_type": "Data",
            "value": "eval: doc.paid_from",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "reference_date",
            "property_type": "Data",
            "value": "eval: doc.paid_from",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "property": "allow_on_submit",
            "fieldname": "cost_center",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "section_break_12",
            "value": "",
            "property_type": "Data",
        },
        {
            "doctype": "Payment Entry",
            "property": "field_order",
            "property_type": "Data",
            "value": json.dumps(MAIN_ORDER_FIELDS),
            "doctype_or_field": "DocType",
        },
        {
            "doctype": "Payment Entry",
            "fieldname": "status",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": 1,
        },
        {
            "doctype": "Payment Entry",
            "doctype_or_field": "DocField",
            "fieldname": "cheque_status",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": 1,
        },

        # Bank Guarantee
        {
            "doctype": "Bank Guarantee",
            "property": "field_order",
            "property_type": "Data",
            "value": json.dumps(BANK_GUARANTEE_FIELDS_ORDER),
            "doctype_or_field": "DocType",
        },
        {
            "doctype": "Bank Guarantee",
            "fieldname": "customer",
            "property": "depends_on",
            "property_type": "Data",
            "value": 'eval: doc.reference_doctype == "Sales Order"',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "fieldname": "supplier",
            "property": "depends_on",
            "property_type": "Data",
            "value": 'eval: doc.reference_doctype == "Purchase Invoice"',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "read_only",
            "property_type": "Check",
            "fieldname": "amount",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "reqd",
            "property_type": "Check",
            "fieldname": "reference_docname",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "no_copy",
            "property_type": "Check",
            "fieldname": "reference_docname",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "label",
            "property_type": "Data",
            "fieldname": "amount",
            "value": "Grand Amount",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "reqd",
            "property_type": "Check",
            "fieldname": "bank_guarantee_number",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "no_copy",
            "property_type": "Check",
            "fieldname": "bank_guarantee_number",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "reqd",
            "property_type": "Check",
            "fieldname": "name_of_beneficiary",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "reqd",
            "property_type": "Check",
            "fieldname": "project",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "fieldtype",
            "property_type": "Data",
            "fieldname": "reference_doctype",
            "value": "Select",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "options",
            "property_type": "Data",
            "fieldname": "reference_doctype",
            "value": "Sales Order\nPurchase Invoice\nPurchase Order",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "quick_entry",
            "property_type": "Check",
            "value": 0,
            "doctype_or_field": "DocType",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "depends_on",
            "fieldname": "margin_details",
            "property_type": "Data",
            "value": 'eval:doc.bank_guarantee_purpose == \'Bank Guarantee\' && doc.bg_type == "Providing" || doc.bank_guarantee_purpose == \'Cheque\' && doc.bg_type=="Providing"',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "depends_on",
            "fieldname": "bank_account",
            "property_type": "Data",
            "value": 'eval:doc.bg_type == "Providing"',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "fetch_from",
            "fieldname": "name_of_beneficiary",
            "property_type": "Small Text",
            "value": '.customer_name',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "fixed_deposit_number",
            "property_type": "Check",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "charges",
            "property_type": "Check",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "margin_money",
            "property_type": "Check",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "depends_on",
            "fieldname": "bank_account_info",
            "property_type": "Data",
            "value": "eval:doc.bank_guarantee_purpose=='Bank Guarantee'||doc.custom_bank_guarantee_purpose=='Cheque'",
            "doctype_or_field": "DocField",
        },
        {
            "doctype:": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "bank_account_no",
            "property_type": "Data",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype:": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "iban",
            "property_type": "Data",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype:": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "branch_code",
            "property_type": "Data",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype:": "Bank Guarantee",
            "property": "hidden",
            "fieldname": "swift_number",
            "property_type": "Data",
            "value": 1,
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "fieldname": "bg_type",
            "property": "fieldtype",
            "property_type": "Data",
            "value": "Select",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "fieldname": "bg_type",
            "property": "options",
            "property_type": "Data",
            "value": "\nProviding\nReceiving",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Bank Guarantee",
            "property": "default",
            "property_type": "Data",
            "fieldname": "bg_type",
            "value": "Providing",
            "doctype_or_field": "DocField",
        },
    ]
    return property_setter
