# How to Alter an Existing Feature

## Adding a new field to an existing feature

Edit the feature module (e.g. `setup/features/banking.py`) and add the field dict to the relevant doctype list. Then re-run customizations on installed sites:

```bash
bench --site <site> execute optima_payment.setup.registry.ensure_customizations
```

The upsert is idempotent — existing fields are untouched, the new field is created.

---

## Changing a field's properties (label, default, depends_on, etc.)

Edit the field dict in the feature module. Re-running `ensure_customizations` will diff the stored values and update only what changed.

```bash
bench --site <site> execute optima_payment.setup.registry.ensure_customizations
```

---

## Renaming a field (fieldname change)

A rename is **not** handled by `ensure_customizations` — it upserts by `fieldname`, so the old field stays and the new one is created alongside it.

**You must write a patch.** The patch should:
1. Copy data from the old column to the new one (if the field stores data).
2. Delete the old `Custom Field` record.
3. Call `create_custom_fields_safely` + `sync_custom_field_schema` to create the new field.

See [how-to-write-a-patch.md](how-to-write-a-patch.md) and `patches/rename_lc_account_to_providing_and_add_receiving.py` for a real example.

Also update the field dict in the feature module so future installs use the new fieldname.

---

## Changing a field's fieldtype

`upsert_custom_field` detects a fieldtype mismatch, deletes the old field, and recreates it. **All stored data in that column is lost.**

If you need to preserve data, write a patch that migrates data before the recreation.

---

## Removing a field

1. Remove it from the feature module's `get_custom_fields()`.
2. Write a patch that deletes the `Custom Field` record:

```python
old_cf = frappe.db.get_value("Custom Field", {"dt": "Some DocType", "fieldname": "old_field"}, "name")
if old_cf:
    frappe.delete_doc("Custom Field", old_cf, force=True)
    frappe.clear_cache(doctype="Some DocType")
```

Removing from the feature module alone only stops the field from being re-created on fresh installs — it does not remove the field from already-installed sites.

---

## Adding or changing a property setter

Edit `get_property_setters()` in the feature module. Re-run `ensure_customizations` — `upsert_property_setter` will create or update it.

```bash
bench --site <site> execute optima_payment.setup.registry.ensure_customizations
```

## Removing a property setter

Move it to `obsolete_property_setters` in the `FeatureSpec`:

```python
FeatureSpec(
    key="payment_workflow",
    ...
    obsolete_property_setters=[
        {"doctype": "Payment Entry", "property": "field_order"},
    ],
)
```

`ensure_customizations` will delete matching property setters on every run. Once confirmed gone from all sites, remove the entry.
