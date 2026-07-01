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
    }
