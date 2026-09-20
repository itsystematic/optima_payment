# How to Add a Setup Feature

A feature is a named group of custom fields and property setters that belong together:
`banking`, `letter_of_credit`, `hrms_integration`.

---

## Step 1 — Create the feature module

Add a file under `setup/features/`. Keep it pure data: no Frappe imports, no side effects, no
queries. It is read on install, in patches and in tests.

```python
# setup/features/supplier_banking.py
"""Supplier banking customizations."""

from __future__ import annotations


def get_custom_fields() -> dict[str, list[dict]]:
    return {
        "Bank Account": [
            {
                "fieldname": "supplier_bank_reference",
                "fieldtype": "Data",
                "label": "Supplier Bank Reference",
                "insert_after": "account_subtype",
            },
        ]
    }


def get_property_setters() -> list[dict]:
    return [
        {
            "doctype": "Bank Account",
            "fieldname": "iban",
            "property": "read_only",
            "property_type": "Check",
            "value": 1,
        },
    ]
```

Omit `get_property_setters` entirely if the feature has none.

---

## Step 2 — Register it

In `setup/registry.py`, import the module and add it to `get_feature_specs()`:

```python
from .features import supplier_banking

FeatureSpec(
    key="supplier_banking",
    get_custom_fields=supplier_banking.get_custom_fields,
    get_property_setters=supplier_banking.get_property_setters,   # omit if none
),
```

For a feature that only applies when another app is installed:

```python
FeatureSpec(
    key="hrms_integration",
    get_custom_fields=hrms_integration.get_custom_fields,
    enabled=lambda: _is_installed("hrms"),
),
```

Declarations from all enabled features are merged by key. Declaring the same field in two features
is fine as long as the two declarations agree; if they differ, the sync stops with
`DeclarationConflict`.

---

## Step 3 — Ship it to installed sites

Fresh installs pick the feature up from `after_install`. Existing sites need a patch:

```python
"""Add the supplier banking fields to Bank Account."""

from optima_payment.setup.sync import sync


def execute() -> None:
    sync()
```

See [how-to-write-a-patch.md](how-to-write-a-patch.md) for registering and testing it.

---

## Field dict reference

| Key | Required | Notes |
|-----|----------|-------|
| `fieldname` | Yes | snake case, unique per doctype, no `custom_` prefix (that is what Frappe gives client-made fields) |
| `fieldtype` | Yes | `Data`, `Link`, `Currency`, `Check`, `Select`, `Date`, … — never changed in place later |
| `label` | Recommended | display label |
| `insert_after` | Recommended | the fieldname this one follows |
| `options` | For Link/Select | Link: target doctype. Select: newline-separated options |
| `default`, `read_only`, `hidden`, `no_copy` | No | `1` / `0` for the flags |
| `depends_on`, `mandatory_depends_on` | No | eval expressions |

## Property setter dict reference

| Key | Required | Notes |
|-----|----------|-------|
| `doctype` | Yes | the doctype being customized |
| `property` | Yes | the property name, e.g. `read_only`, `depends_on`, `label` |
| `value` | Yes | the value to store |
| `fieldname` | For field-level | omit for a doctype-level property |
| `property_type` | Recommended | `Check`, `Data`, `Text`, … — defaults to `Data` |
| `row_name` | Rarely | for a grid row property |

Never declare `field_order`; see [questions-and-answers.md](questions-and-answers.md).
