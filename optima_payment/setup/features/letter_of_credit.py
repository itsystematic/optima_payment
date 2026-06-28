"""Letter of Credit setup isolated from other Optima Payment domains."""

from __future__ import annotations


def get_custom_fields() -> dict[str, list[dict]]:
    """Return Letter of Credit custom fields owned by Optima Payment."""
    return {
        "Payment Entry": [
            {
                "fieldname": "letter_of_credit",
                "fieldtype": "Link",
                "label": "Letter of Credit",
                "options": "Letter of Credit",
                "insert_after": "reference_no",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "is_lc_commission_entry",
                "fieldtype": "Check",
                "label": "Is Letter of Credit Commission Entry",
                "insert_after": "letter_of_credit",
                "default": 0,
                "hidden": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "is_lc_loss_entry",
                "fieldtype": "Check",
                "label": "Is Letter of Credit Loss Entry",
                "insert_after": "is_lc_commission_entry",
                "default": 0,
                "hidden": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "is_system_generated",
                "fieldtype": "Check",
                "label": "Is System Generated",
                "insert_after": "naming_series",
                "default": 0,
                "no_copy": 1,
                "read_only": 1,
                "depends_on": "eval:doc.is_system_generated == 1;",
            },
        ],
    }


def get_property_setters() -> list[dict]:
    """Return Letter of Credit property setters owned by Optima Payment."""
    return [
        {
            "doctype": "Payment Entry",
            "fieldname": "taxes",
            "property": "depends_on",
            "property_type": "Data",
            "value": (
                "eval: doc.party_type == 'Supplier' || doc.party_type == 'Customer' "
                "|| (doc.letter_of_credit && doc.is_system_generated)"
            ),
            "doctype_or_field": "DocField",
        },
    ]
