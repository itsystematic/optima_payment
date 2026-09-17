"""Bring a site's Optima Payment custom fields and property setters in line with the feature
declarations, without overwriting what the client changed in Customize Form.

Ownership follows Frappe v15's ``is_system_generated`` flag:

- A declared Custom Field row at flag 1 belongs to the app. Customize Form saves client edits to
  such a field as separate Property Setters, so updating the row loses nothing. A row at flag 0
  holds edits in place, so it is left alone.
- A declared Property Setter belongs to the app only while its row keeps flag 1. When the client
  edits the same key in Customize Form, Frappe replaces the row with a flag-0 one. A flag-0 row
  that still holds the declared value carries no client edit, so uninstall removes it.
- ``field_order`` stores a doctype's whole form order, so it is never synced; it is only written
  at install where the site has none.
- A fieldtype change is never applied in place; it is reported as a conflict.
- Nothing here adopts flag-0 rows. The one-time patch ``adopt_existing_customizations`` did that for
  customizations created before ownership was tracked.

The entry points below are what the install and uninstall hooks and patches call.
``declarations`` reads the features, ``custom_fields`` and ``property_setters`` compare them with
the site, and ``report`` prints the outcome.
"""

from __future__ import annotations

from .report import Change, report
from . import custom_fields, property_setters
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


def apply_starting_field_orders(dry_run: bool = False) -> list[Change]:
    """Write each declared ``field_order`` only where the doctype has no ``field_order`` property setter.

    Install only. An existing one may be the client's, and Customize Form rewrites the whole value
    on every move, so it is never compared or replaced.
    """
    changes = property_setters.create_missing_field_orders(get_declared_property_setters(), dry_run)
    report("Optima Payment starting field orders", changes, dry_run)
    return changes


def remove_customizations(dry_run: bool = False) -> list[Change]:
    """Delete the declared custom fields and the declared property setters the app still owns.

    A declared property setter at flag 0 with a value different from code is the client's and stays.
    Deleting a custom field also deletes every property setter on that field, the client's included.
    """
    declared_fields = get_declared_custom_fields()
    changes = custom_fields.remove(declared_fields, dry_run)
    changes += property_setters.remove(get_declared_property_setters(), declared_fields, dry_run)
    report("Optima Payment customization removal", changes, dry_run)
    return changes
