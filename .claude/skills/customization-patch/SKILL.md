---
name: customization-patch
description: Create and register a Frappe migration patch in optima_payment that pushes new custom fields or property setters from the setup registry out to already-installed sites. Use when custom fields or property setters have been added under setup/features/ and existing sites need them, or when asked to "add a patch", "write a migration patch", or "make this reach the other sites".
---

Custom fields and property setters defined under `optima_payment/setup/features/` are applied on
install. Sites that already have the app installed never re-run that step — a patch is what carries
the new definitions to them.

## When to use

Whenever new custom fields or property setters are added to a feature module under
`optima_payment/setup/features/` and those changes need to reach sites that already have the app
installed (not just fresh installs).

## What to ask before writing the patch

If the user hasn't provided it, ask:

- **What was added?** (e.g. "is_lc_close_entry on Payment Entry, pre_close_status and reopen_date
  on Letter of Credit") — used for the patch docstring only.
- **Patch name** — derive it from the feature and what was added, e.g.
  `add_letter_of_credit_close_reopen_fields`. Snake_case, descriptive, no version prefix.
  Confirm with the user if unsure.

## File to create

`optima_payment/patches/<patch_name>.py`

### Template

```python
"""<One-line summary of what this patch adds / fixes on existing sites>.

Adds to <DocType>:
- <fieldname> (<fieldtype>, <notable flags like hidden / read-only>)
...
"""
from optima_payment.setup.registry import ensure_customizations


def execute():
    ensure_customizations()
```

Rules:

- The docstring **must** list every new field or property setter so future readers know what the
  patch was for without diffing git.
- The body is always the same two lines — import + call. Do not inline field definitions; they
  already live in the feature module.
- `ensure_customizations()` is idempotent — safe to re-run, existing fields are updated in place
  (upsert), not duplicated.

## Register the patch

Append the dotted module path to the `[post_model_sync]` section of `optima_payment/patches.txt`:

```
optima_payment.patches.<patch_name>
```

Always append — never insert above existing entries, as Frappe tracks patches by position and name
in `__PatchLog`.

## Verify

After writing and registering, confirm:

1. The patch file exists at the correct path.
2. `patches.txt` has the new entry at the bottom of `[post_model_sync]`.
3. The docstring lists every field/setter added in this batch.

Do **not** run the patch automatically — leave that to the user with:

```bash
bench --site <sitename> migrate
```
