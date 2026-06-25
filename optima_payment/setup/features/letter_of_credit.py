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
