"""Move Bank Account.bank_guarantee_account below account_subtype and add the Letter of Credit fields.

bank_guarantee_account used to be inserted after "company". Only a row still holding exactly that
old app value is moved, so a position the client chose stays, and the later adoption does not keep
the old value as a client setting. ``sync()`` then creates the Letter of Credit account fields.
"""

import frappe

from optima_payment.setup.sync import sync


def execute() -> None:
    frappe.db.set_value(
        "Custom Field",
        {"dt": "Bank Account", "fieldname": "bank_guarantee_account", "insert_after": "company"},
        "insert_after",
        "account_subtype",
        update_modified=False,
    )
    frappe.clear_cache(doctype="Bank Account")
    sync()
