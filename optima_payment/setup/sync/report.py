"""The change records every sync step returns, and the console report built from them."""

from __future__ import annotations

from dataclasses import dataclass

import click

ACTION_COLORS = {
    "create": "green",
    "update": "cyan",
    "adopt": "magenta",
    "remove": "bright_red",
    "keep": "white",
    "conflict": "red",
    "missing": "yellow",
}


@dataclass(frozen=True)
class Change:
    """One planned or applied change, as shown in the sync report."""

    action: str
    target: str
    detail: str = ""

    def __str__(self) -> str:
        suffix = f"  {self.detail}" if self.detail else ""
        return f"{self.action:<8} {self.target}{suffix}"


def report(title: str, changes: list[Change], dry_run: bool) -> None:
    mode = "preview, nothing written" if dry_run else "applied"
    click.secho(f"{title} ({mode}): {len(changes)} item(s)", fg="blue")
    for change in changes:
        click.secho(f"   {change}", fg=ACTION_COLORS[change.action])
