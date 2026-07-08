"""Uninstall entrypoint for Optima Payment."""

from __future__ import annotations

from click import secho

from optima_payment.setup.permissions import remove_access_control
from optima_payment.setup.registry import before_uninstall as run_before_uninstall


def before_uninstall_entrypoint() -> None:
    """Remove Optima-owned customizations before the app is uninstalled."""
    run_before_uninstall()
    remove_access_control()
    secho("Uninstall Optima Payment Complete Successfully", fg="green")


def before_uninstall() -> None:
    """Backward-compatible uninstall hook used by Frappe."""
    before_uninstall_entrypoint()

