"""Time Based Overdue Limit setup: the index its overdue-invoice lookup reads through."""

from __future__ import annotations


def get_indexes() -> dict[str, list[list[str]]]:
    """Return the indexes the overdue check needs, by doctype.

    ``get_oldest_overdue_invoice`` runs on every Sales Invoice and Sales Order save. ERPNext indexes
    ``customer`` alone, so the lookup read every invoice the customer ever had. This index holds
    every column the lookup filters, sorts and returns: the exact matches first, then ``status``,
    then ``due_date`` for the sort.
    """
    return {"Sales Invoice": [["customer", "company", "status", "due_date"]]}
