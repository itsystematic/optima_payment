import json
import frappe
from frappe import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
def execute():
    update_bank_guarantee()


def update_bank_guarantee():
    # frappe.reload_doc("custom", "doctype", "bank_guarantee", force=True)
    custom_fields = get_custom_fields()

    create_custom_fields(custom_fields, update=True)
    add_additional_property_setter()
    


def add_additional_property_setter():
    property_setter = get_property_setters()
    for ps in property_setter:
        make_property_setter(ps)


def get_custom_fields():
    custom_fields = {
        "Letter Head": [
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
        "Bank": [
            {
                "fieldname": "company",
                "label": "Company",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "website" 
            },
        ],
        "Bank Account": [
            {
                "fieldname": "bank_guarantee_account",
                "fieldtype": "Link",
                "label": "Bank Guarantee Account",
                "insert_after": "company",
                "options": "Account",
            },
        ],
        "Company": [
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
                "reqd": 1,
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
            # {
            #     "fieldname": "column_break_123",
            #     "fieldtype": "Column Break",
            #     "label": "",
            #     "insert_after": "Name of Beneficiary",
            # },
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

    return custom_fields

def get_property_setters():
    property_setter = [
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
            "property": "default",
            "property_type": "Text",
            "fieldname": "reference_doctype",
            "value": "Sales Order",
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
            "property": "read_only",
            "property_type": "Check",
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