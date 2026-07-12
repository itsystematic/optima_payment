"""Re-sync Bank Account custom fields after the banking feature schema changed.

bank_guarantee_account moved from insert_after "company" to "account_subtype",
and the new letter_of_credit_account field was added after it. Custom fields
are only upserted automatically on fresh installs (after_install), so
already-installed sites need this patch to pick up both changes.
"""

import click

from optima_payment.setup.features import bank_guarantee, letter_of_credit
from optima_payment.setup.metadata import create_custom_fields_safely, sync_custom_field_schema


def execute() -> None:
    custom_fields = {
        "Bank Account": [
            *bank_guarantee.get_custom_fields()["Bank Account"],
            *letter_of_credit.get_custom_fields()["Bank Account"],
        ]
    }

    create_custom_fields_safely(custom_fields)
    sync_custom_field_schema(custom_fields)

    click.secho("Re-synced Bank Account custom fields for Optima Payment", fg="green")