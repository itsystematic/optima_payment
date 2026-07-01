# How to Write a Patch

Patches handle schema changes that `ensure_customizations` cannot — renames, deletions, and data migrations — on already-installed sites.

---

## When to write a patch vs. just editing the feature module

| Change | Feature module edit enough? | Patch needed? |
|--------|-----------------------------|---------------|
| Add a new field | Yes | No |
| Change label / default / depends_on | Yes | No |
| Rename a field | No | Yes — old field stays as orphan |
| Remove a field | No | Yes — field stays on installed sites |
| Change fieldtype | No | Yes — data loss risk |
| Move data between fields | No | Yes |

---

## Step 1 — Create the patch file

Add a file in `patches/`. Name it descriptively in snake_case.

```python
# patches/my_patch.py
"""One-line summary of what this patch does and why."""

import click
import frappe

from optima_payment.setup.features import my_feature
from optima_payment.setup.metadata import create_custom_fields_safely, sync_custom_field_schema


def execute() -> None:
    # ... your migration logic ...

    # Re-sync affected custom fields so the new state is applied
    custom_fields = {"Some DocType": my_feature.get_custom_fields()["Some DocType"]}
    create_custom_fields_safely(custom_fields)
    sync_custom_field_schema(custom_fields)

    click.secho("Patch description complete", fg="green")
```

---

## Step 2 — Register it in patches.txt

Add it to the bottom of the `[post_model_sync]` section:

```
[post_model_sync]
...
optima_payment.patches.my_patch
```

`post_model_sync` means the patch runs after Frappe has synced DocType schemas — correct for custom field work. Use `pre_model_sync` only if your patch must run before schema sync (rare).

---

## Step 3 — Test it

```bash
bench --site <site> migrate
```

The patch runs once. To re-run it during development, delete the patch record from the site DB:

```bash
bench --site <site> console
>>> frappe.db.delete("Patch Log", {"patch": "optima_payment.patches.my_patch"})
>>> frappe.db.commit()
```

Then run `bench migrate` again.

---

## Rename pattern (real example: `patches/rename_lc_account_to_providing_and_add_receiving.py`)

```python
def execute() -> None:
    _migrate_existing_data()    # copy old column → new column
    _remove_old_custom_field()  # delete the old Custom Field record
    # create new fields via create_custom_fields_safely + sync_custom_field_schema

def _migrate_existing_data() -> None:
    if not frappe.db.has_column("tabBank Account", OLD_FIELDNAME):
        return  # guard: column may not exist if the patch runs twice
    frappe.db.sql(
        f"UPDATE `tabBank Account` SET `{NEW_FIELDNAME}` = `{OLD_FIELDNAME}` "
        f"WHERE `{OLD_FIELDNAME}` IS NOT NULL AND `{OLD_FIELDNAME}` != ''"
    )

def _remove_old_custom_field() -> None:
    old_cf = frappe.db.get_value("Custom Field", {"dt": "Bank Account", "fieldname": OLD_FIELDNAME}, "name")
    if old_cf:
        frappe.delete_doc("Custom Field", old_cf, force=True)
        frappe.clear_cache(doctype="Bank Account")
```

Key rules:
- Always guard with `has_column` or existence checks so the patch is safe to re-run.
- Migrate data **before** deleting the old field.
- Call `frappe.clear_cache(doctype=...)` after any Custom Field deletion.
