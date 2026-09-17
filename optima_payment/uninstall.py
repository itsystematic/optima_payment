"""Uninstall entrypoint for Optima Payment."""

from __future__ import annotations

from click import secho

from optima_payment.setup.permissions import remove_access_control
from optima_payment.setup.sync import remove_customizations


def before_uninstall_entrypoint() -> None:
    """Remove Optima-owned customizations before the app is uninstalled."""
    remove_customizations()
    remove_access_control()
    secho("Uninstall Optima Payment Complete Successfully", fg="green")


def before_uninstall() -> None:
    """Backward-compatible uninstall hook used by Frappe."""
    before_uninstall_entrypoint()

