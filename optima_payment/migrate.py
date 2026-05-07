"""Migrate entrypoint for Optima Payment."""

from __future__ import annotations

from click import secho

from optima_payment.setup import update_fields_in_database


def after_migrate() -> None:
    """Apply stable post-migrate updates that remain safe across app versions."""
    update_fields_in_database()
    secho("Updated Optima Payment customizations and field options successfully", fg="green")
