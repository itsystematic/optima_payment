---
name: customization-patch
description: Create and register a Frappe migration patch in optima_payment that carries a change in the setup feature declarations — a new custom field or property setter, an edited one, a rename or a removal — out to already-installed sites. Use when something under setup/features/ changed and existing sites need it, or when asked to "add a patch", "write a migration patch", or "make this reach the other sites".
---

Custom fields and property setters declared under `optima_payment/setup/features/` are written to a
site on install. Nothing re-applies them on every migrate, deliberately: re-applying is what used to
overwrite what clients changed in Customize Form. **One patch per change** is how a change reaches
installed sites.

Full background: `docs/setup/architecture.md`, `docs/setup/questions-and-answers.md`, and
`docs/setup/how-to-write-a-patch.md` — read the last one before writing anything unusual.

## What `sync()` will and will not do

`optima_payment.setup.sync.sync()` compares the declarations with the site and:

- **creates** a declared row that is missing,
- **updates** a row the app owns (`is_system_generated = 1`) that drifted from code,
- **keeps** any row the site owns (flag 0) — the client's edits always win,
- **reports a conflict** instead of changing a fieldtype in place,
- **never touches** `field_order`, and never touches anything the app does not declare.

So a patch that only adds or edits a declaration needs nothing but `sync()`. Anything else —
renames, removals, data migration — is extra code in the same patch.

## What to ask before writing

If the user has not said:

- **What changed?** e.g. "is_lc_close_entry on Payment Entry; pre_close_status and reopen_date on
  Letter of Credit". This goes in the docstring, which Frappe prints during migrate.
- **Patch name** — from the feature and the change, snake_case, no version prefix:
  `add_letter_of_credit_close_reopen_fields`. Confirm if unsure.

## File to create

`optima_payment/patches/<patch_name>.py`

```python
"""<One line: what changes on existing sites>.

Adds to <DocType>:
- <fieldname> (<fieldtype>, <notable flags>)
"""

from optima_payment.setup.sync import sync


def execute() -> None:
    sync()
```

Rules:

- The docstring **must** name every field or property setter involved, so a reader knows what the
  patch was for without diffing git.
- Do not inline field definitions; they live in the feature module.
- Do not call anything else "just in case". There is no `ensure_customizations`, no
  `setup.metadata` — those were removed.

## Beyond adding a field

| Change | Patch body |
|--------|-----------|
| Rename a field | `sync()` first (creates the new field), then copy the data into empty targets only, then delete the old Custom Field row |
| Remove a field | delete the Custom Field row by `dt` + `fieldname`; Frappe removes the property setters on it too |
| Remove a property setter | delete by the **full key**: `doc_type` + `field_name` + `property`. Never by doctype + property alone — that matches the client's rows and is what wiped the Payment Entry layout on live sites |
| Change a fieldtype | not in place. New fieldname + data migration + removal of the old field |

Guard every step (`frappe.db.has_column`, `frappe.db.exists`) so the patch survives a site where
part of the work already happened. Creating a field commits, so a patch that creates and then fails
cannot be rolled back.

## Register the patch

Append the dotted path as the **last** line of the `[post_model_sync]` section in
`optima_payment/patches.txt`:

```
optima_payment.patches.<patch_name>
```

Always append. A patch is identified by that exact line, comment included: editing the line makes
Frappe run it again everywhere, editing the file does not.

## Verify

1. The patch file exists at the right path and imports `sync` from `optima_payment.setup.sync`.
2. `patches.txt` has the new entry last under `[post_model_sync]`.
3. The docstring names every field or setter in this change.
4. The declaration in `setup/features/` matches what the docstring claims.

Do **not** run the patch. Hand the user the sequence, which checks the forms as well:

```bash
bench --site <sitename> backup
bench --site <sitename> execute optima_payment.setup.sync.preview          # what will change
bench --site <sitename> execute optima_payment.setup.form_snapshot.save
bench --site <sitename> migrate
bench --site <sitename> execute optima_payment.setup.form_snapshot.diff    # what did change
```
