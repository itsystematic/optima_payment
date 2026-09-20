# How to Write a Setup Patch

Every change to a feature declaration reaches already-installed sites through **one patch per
change**. Nothing re-applies the declarations on every migrate — see
[architecture.md](architecture.md) for why.

---

## Step 1 — Write the patch

`patches/add_supplier_bank_fields.py`:

```python
"""Add the supplier bank fields to Bank Account.

Adds to Bank Account:
- supplier_bank_reference (Data)
- supplier_bank_branch (Data, hidden)
"""

from optima_payment.setup.sync import sync


def execute() -> None:
    sync()
```

The **docstring is the changelog**: Frappe prints it while the patch runs, so write what changes,
not how. The body calls `sync()`, which creates what is missing and updates rows the app owns,
leaving everything the site owns alone.

Anything beyond adding or editing a declaration — a rename, a removal, a data migration — goes in
the same patch, around the `sync()` call. See the patterns below.

---

## Step 2 — Register it

Add it as the **last** line of `patches.txt` under `[post_model_sync]`:

```
[post_model_sync]
...
optima_payment.patches.adopt_existing_customizations
optima_payment.patches.add_supplier_bank_fields
```

`post_model_sync` is right for custom field work: doctype schemas are already synced by then.

A patch is identified by that exact line, comment included. Changing the file later does **not**
re-run it anywhere.

---

## Step 3 — Try it on a site

```bash
bench --site <site> backup
bench --site <site> execute optima_payment.setup.form_snapshot.save
bench --site <site> migrate
bench --site <site> execute optima_payment.setup.form_snapshot.diff
```

The diff should report only what you intended. To run the patch again while developing:

```bash
bench --site <site> console
>>> frappe.db.delete("Patch Log", {"patch": "optima_payment.patches.add_supplier_bank_fields"})
>>> frappe.db.commit()
```

---

## Pattern — rename a field

Create first, copy second, delete last. Real example:
`patches/rename_lc_account_to_providing_and_add_receiving.py`.

```python
def execute() -> None:
    sync()                      # the new field exists after this line
    _migrate_existing_data()    # copy old column → new column, where the new one is empty
    _remove_old_custom_field()  # delete the old Custom Field row
```

```python
def _migrate_existing_data() -> None:
    if not frappe.db.has_column("Bank Account", OLD_FIELDNAME):
        return

    frappe.db.sql(
        f"""
        UPDATE `tabBank Account`
        SET `{NEW_FIELDNAME}` = `{OLD_FIELDNAME}`
        WHERE IFNULL(`{OLD_FIELDNAME}`, '') != ''
            AND IFNULL(`{NEW_FIELDNAME}`, '') = ''
        """
    )
```

Rules that keep this safe:

- **Never copy into a column before `sync()` has created it.** Doing that is what once ended a
  migrate with `Unknown column …`.
- **Only fill empty targets**, so a value someone already entered in the new field is not replaced.
- **Guard every step** with `has_column` / `exists`, so the patch survives a site where half the
  work was already done.
- Update the declaration in `setup/features/` too, so fresh installs get the new name.

---

## Pattern — remove a field

```python
def execute() -> None:
    name = frappe.db.get_value("Custom Field", {"dt": "Bank Account", "fieldname": "old_field"}, "name")
    if name:
        frappe.delete_doc("Custom Field", name, force=True)
```

Deleting the Custom Field also deletes every Property Setter on that field, the client's included —
that is correct, since the field is gone. Frappe leaves the column and its data in the table.

Remove the declaration from the feature module in the same commit.

---

## Pattern — change a fieldtype

Don't, not in place. `sync()` reports a `conflict` and writes nothing, because rewriting the column
can lose data. Declare a **new fieldname**, migrate the data in a patch, then remove the old field.

---

## What a patch must not do

- **Do not re-apply everything** "just in case". `sync()` already limits itself to declared keys and
  app-owned rows.
- **Do not delete a Property Setter by doctype + property alone.** That matches the client's row
  too. This is how the Payment Entry layout was wiped on live sites.
- **Do not assume the patch runs on a fresh site.** `install-app` marks every patch as already
  applied, so patches only ever run on sites installed *before* the patch existed.
