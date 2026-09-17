"""Bring a site's Optima Payment custom fields and property setters in line with the feature
declarations, without overwriting what the client changed in Customize Form.

Ownership follows Frappe v15's ``is_system_generated`` flag:

- A declared Custom Field row at flag 1 belongs to the app. Customize Form saves client edits to
  such a field as separate Property Setters, so updating the row loses nothing. A row still at
  flag 0 holds client edits in place, so it is left alone until it has been adopted.
- A declared Property Setter belongs to the app only while its row keeps flag 1. When the client
  edits the same key in Customize Form, Frappe replaces the row with a flag-0 one.
- ``field_order`` stores a doctype's whole form order, so it is never synced.
- A fieldtype change is never applied in place; it is reported as a conflict.

The entry points below are what install hooks and patches call. ``declarations`` reads the
features, ``custom_fields``, ``property_setters`` and ``adoption`` compare them with the site, and
``report`` prints the outcome.
"""

from __future__ import annotations

from .report import Change, report
from . import adoption, custom_fields, property_setters
from .declarations import get_declared_custom_fields, get_declared_property_setters


def sync(dry_run: bool = False) -> list[Change]:
    """Create missing customizations and update app-owned ones that drifted from their declaration."""
    changes = custom_fields.sync(get_declared_custom_fields(), dry_run)
    changes += property_setters.sync(get_declared_property_setters(), dry_run)
    report("Optima Payment customization sync", changes, dry_run)
    return changes


def preview() -> list[Change]:
    """Show what ``sync`` would change on this site without writing anything."""
    return sync(dry_run=True)


def adopt_custom_fields(dry_run: bool = False) -> list[Change]:
    """Move declared fields still at is_system_generated=0 to flag 1 without changing the form."""
    changes = adoption.adopt(get_declared_custom_fields(), dry_run)
    report("Optima Payment custom field adoption", changes, dry_run)
    return changes

