# Setup Architecture

This document covers how `optima_payment` installs, migrates, and uninstalls its customizations — and how to work with the setup system as a developer.

---

## What "setup" means here

Optima Payment extends standard ERPNext/Frappe doctypes (Payment Entry, Bank Guarantee, Mode of Payment, etc.) with custom fields and property setters. These cannot live in the app's own DocType JSON files because they belong to doctypes owned by other apps.

The setup system manages the full lifecycle of these customizations: creating them on install, migrating them when they change, and removing them on uninstall.

---

## Entry points

| Hook | File | What it does |
|------|------|--------------|
| `after_install` | `install.py → after_install()` | Fresh install: seeds print formats, patches field options, applies all feature customizations, seeds access control (roles + Custom DocPerms) |
| `after_app_install` | `install.py → after_app_install(app_name)` | Fired when **any** app is installed on the site (Frappe passes its name). No-ops unless the app is `hrms`, then applies the HRMS feature's custom fields and HRMS permission grid — covers HRMS being installed *after* Optima Payment |
| `after_migrate` | `migrate.py → after_migrate()` | After every `bench migrate`: re-applies stable field option patches |
| `before_uninstall` | `uninstall.py → before_uninstall()` | Before uninstall: removes feature-owned custom fields, property setters, and access control (Custom DocPerms + unassigned roles) |

These hooks are registered in `hooks.py`.

---

## Call graph — fresh install

```
bench install-app optima_payment
  └── hooks.py: after_install
        └── install.py: after_install()
              ├── standard_data.add_standard_data()       # import files/print_format.json (seed)
              ├── standard_data.update_fields_in_database()  # patch Mode of Payment type options
              ├── registry.ensure_customizations()        # apply enabled feature custom fields + property setters
              ├── permissions.apply_access_control()      # seed Optima roles + Custom DocPerms (install only;
              │                                           #   HRMS grid included only if HRMS is installed)
              └── migration_artifact.import_cheque_legacy_artifact()
```

```
bench install-app hrms          # on a site that already has optima_payment
  └── hooks.py: after_app_install ("hrms")
        └── install.py: after_app_install("hrms")
              ├── registry.ensure_hrms_customizations()   # apply the hrms_integration feature only
              └── permissions.apply_hrms_access_control() # apply HRMS_ROLE_PERMISSIONS
```

```
registry.ensure_customizations()
  └── for each FeatureSpec in get_feature_specs():
        _apply_feature(feature)
          ├── metadata.create_custom_fields_safely(custom_fields)
          ├── metadata.sync_custom_field_schema(custom_fields)
          ├── metadata.add_property_setters(property_setters)
          └── metadata.cleanup_obsolete_property_setters(obsolete)
```

Each step inside `_apply_feature()` runs inside a DB savepoint. A failure rolls back that step without corrupting the rest of the install.

---

## Layer map

```
install.py / migrate.py / uninstall.py   ← entry points (wired in hooks.py)
setup/registry.py                         ← feature registry + lifecycle orchestration
setup/runner.py                           ← step execution with savepoints
setup/metadata.py                         ← CRUD on Custom Field + Property Setter records
setup/standard_data.py                    ← print format seed import + raw field option patches
setup/permissions.py                      ← Optima roles + Custom DocPerm grid (install only)
setup/features/
  banking.py                              ← Bank, Bank Account, Letter Head, GL Entry fields
  payment_workflow.py                     ← Mode of Payment + Payment Entry fields/property setters
  bank_guarantee.py                       ← Bank Guarantee custom fields + property setters
  letter_of_credit.py                     ← Payment Entry LC fields + property setters
  hrms_integration.py                     ← Expense Claim Detail fields (optional)
```

---

## Features and the registry

Each feature is declared as a `FeatureSpec` in `registry.py:get_feature_specs()`:

```python
FeatureSpec(
    key="banking",
    label="Banking customizations",
    get_custom_fields=banking.get_custom_fields,   # returns dict[doctype, list[field_dict]]
    get_property_setters=banking.get_property_setters,  # returns list[property_setter_dict]
    obsolete_property_setters=[...],               # cleaned up on every run
    enabled=lambda: True,                          # or a predicate e.g. _is_installed("hrms")
    is_optional=False,                             # True = skip+log on failure instead of abort
)
```

Features run **in order** — put dependencies before dependents.

---

## How upserts work

`metadata.upsert_custom_field()` is idempotent:
- If the field does not exist → creates it.
- If it exists with the same values → skips (no write).
- If it exists with different values → updates only the changed keys.
- If the `fieldtype` changed → deletes and recreates (fieldtype changes require a schema drop).

This means `ensure_customizations()` is safe to re-run at any time.

---

## Three kinds of seeded state (know the difference)

The setup system manages three distinct kinds of things, with different lifecycles:

| Kind | Lives in | Applied | Reversed on uninstall? |
|------|----------|---------|------------------------|
| **Schema customizations** — custom fields, property setters | `setup/features/*` via `registry.py` | install + re-runnable | **Yes** (feature framework) |
| **Access control** — Optima roles + Custom DocPerms | `setup/permissions.py` (code) | **install only** | **Yes** (docperms removed; unassigned roles deleted) |
| **Data seed** — print formats | `files/print_format.json` via `import_doc` | **install only** | **No** (intentional — 75 KB of opaque HTML admins may edit per-site) |

Access control is **install only** on purpose: like the print-format seed, admins may tune
per-site permissions afterwards and a later `bench migrate` must not overwrite them. See
[permissions.md](permissions.md) for the roles, why they exist, and how to edit the grid.

## Standard data files

`files/` contains JSON fixtures imported once at install time via `standard_data.add_standard_data()`. The import order is defined explicitly in `STANDARD_DATA_FILES`:

```python
STANDARD_DATA_FILES = [
    "print_format.json",
]
```

Missing files are skipped with a warning — they do not abort the install. (Roles and Custom
DocPerms used to live here too; they moved to `setup/permissions.py` — code, reversible.)

---

## Re-running all customizations on an installed site

```bash
bench --site <site> execute optima_payment.setup.registry.ensure_customizations
```

This is safe to run at any time. It upserts all custom fields and property setters across all enabled features.

---

## Patches

When a field definition changes on an **already-installed** site, `ensure_customizations()` alone is not enough for renames or deletions (it only upserts by fieldname). A **patch** is needed.

Patches live in `patches/` and are registered in `patches.txt` under `[post_model_sync]`.

```
bench --site <site> migrate   ← runs all pending patches automatically
```

Each patch runs exactly once per site. See [how-to-write-a-patch.md](how-to-write-a-patch.md) for guidance.
