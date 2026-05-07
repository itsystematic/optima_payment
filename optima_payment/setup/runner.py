"""Shared setup runner utilities for Optima Payment lifecycle steps."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import click
import frappe

SetupCallable = Callable[[], None]
SetupStep = tuple[str, SetupCallable]


class SetupStepError(Exception):
    """Wrap a failed setup step with section and step context."""

    def __init__(self, section_label: str, step_label: str, original_error: Exception):
        self.section_label = section_label
        self.step_label = step_label
        self.original_error = original_error
        super().__init__(
            f"{section_label} -> {step_label}: {describe_exception(original_error)}"
        )


def describe_exception(error: Exception) -> str:
    """Return a readable exception message for CLI and log output."""
    message = str(error).strip()
    if message:
        return f"{error.__class__.__name__}: {message}"

    if getattr(error, "args", None):
        args_message = " | ".join(str(arg).strip() for arg in error.args if str(arg).strip())
        if args_message:
            return f"{error.__class__.__name__}: {args_message}"

    return error.__class__.__name__


def run_setup_steps(steps: Sequence[SetupStep], section_label: str | None = None) -> None:
    """Run setup steps sequentially with savepoint-level failure reporting."""
    if section_label:
        click.secho(f"{section_label}...", fg="yellow")

    total_steps = len(steps)
    for index, (step_label, step_fn) in enumerate(steps, start=1):
        savepoint = f"optima_payment_setup_step_{index}"
        click.secho(f"   [{index}/{total_steps}] {step_label}", fg="cyan")
        frappe.db.savepoint(savepoint)

        try:
            step_fn()
        except Exception as error:
            # DDL can invalidate savepoints in MariaDB, so rollback failure should not
            # hide the actual step failure that the operator needs to see.
            try:
                frappe.db.rollback(save_point=savepoint)
            except Exception as rollback_error:
                frappe.log_error(
                    title="Optima Payment setup rollback failed",
                    message=(
                        f"Failed to rollback savepoint {savepoint} while handling "
                        f"{step_label}: {describe_exception(rollback_error)}"
                    ),
                )
            raise SetupStepError(section_label or "Optima Payment setup", step_label, error) from error
