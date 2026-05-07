"""Feature-oriented setup lifecycle for Optima Payment."""

from __future__ import annotations

import click

from optima_payment.setup.registry import (
    before_uninstall,
    ensure_customizations,
    get_all_custom_fields,
    get_all_property_setters,
)
from optima_payment.setup.runner import SetupStepError, describe_exception, run_setup_steps
from optima_payment.setup.standard_data import add_standard_data, update_fields_in_database


def prepare_setup() -> None:
    """Install standard data, update stable metadata, and apply feature setup."""
    click.secho("Setting up Optima Payment customizations...", fg="blue")
    run_setup_steps(
        [
            ("Install standard data", add_standard_data),
            ("Update standard field options", update_fields_in_database),
            ("Apply schema customizations", ensure_customizations),
        ],
        section_label="Optima Payment setup",
    )


def get_custom_fields() -> dict[str, list[dict]]:
    """Return all enabled Optima Payment custom fields."""
    return get_all_custom_fields()


def get_property_setter() -> list[dict]:
    """Return all enabled Optima Payment property setters."""
    return get_all_property_setters()


__all__ = [
    "SetupStepError",
    "add_standard_data",
    "before_uninstall",
    "describe_exception",
    "ensure_customizations",
    "get_custom_fields",
    "get_property_setter",
    "prepare_setup",
    "run_setup_steps",
    "update_fields_in_database",
]
