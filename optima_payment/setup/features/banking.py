"""Banking-related setup for shared payment support doctypes."""

from __future__ import annotations


def get_custom_fields() -> dict[str, list[dict]]:
    """Return banking custom fields owned by Optima Payment."""
    return {
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
            {
                "fieldname": "company",
                "label": "Company",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "website",
            },
        ],
        "Letter Head": [
            {
                "fieldname": "is_box",
                "fieldtype": "Check",
                "label": "Box",
                "insert_after": "is_default",
            },
            {
                "fieldname": "customer",
                "fieldtype": "Link",
                "label": "Customer",
                "insert_after": "reference_docname",
                "options": "Customer",
                "depends_on": 'eval: doc.reference_doctype == "Sales Order"',
            },
            {
                "fieldname": "supplier",
                "fieldtype": "Link",
                "label": "Supplier",
                "insert_after": "customer",
                "options": "Supplier",
                "depends_on": 'eval: doc.reference_doctype == "Purchase Invoice"',
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
            {
                "fieldname": "is_bank_guarantee_comission_entry",
                "fieldtype": "Check",
                "label": "Bank Guarantee Comission Entry",
                "insert_after": "transaction_exchange_rate",
                "default": 0,
                "hidden": 1,
            }
        ],
    }
