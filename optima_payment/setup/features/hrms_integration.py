"""Optional HRMS integration customizations for Optima Payment."""

from __future__ import annotations


def get_custom_fields() -> dict[str, list[dict]]:
    """Return HRMS-only custom fields owned by Optima Payment."""
    return {
        "Expense Claim Detail": [
            {
                "fieldname": "purchase_invoice",
                "fieldtype": "Link",
                "label": "Purchase Invoice",
                "options": "Purchase Invoice",
            }
        ]
    }
