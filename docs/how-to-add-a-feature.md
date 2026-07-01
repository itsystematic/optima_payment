# How to Add a Setup Feature

A "feature" is a named group of custom fields and/or property setters that belong together. Examples: `banking`, `letter_of_credit`, `hrms_integration`.

---

## Step 1 — Create the feature module

Add a file under `setup/features/`. Keep it pure data — no Frappe imports, no side effects.

```python
# setup/features/my_feature.py
"""My feature setup — custom fields and property setters."""

from __future__ import annotations


def get_custom_fields() -> dict[str, list[dict]]:
    return {
        "Some DocType": [
            {
                "fieldname": "my_custom_field",
                "fieldtype": "Data",
                "label": "My Custom Field",
                "insert_after": "some_existing_field",
            },
        ]
    }


def get_property_setters() -> list[dict]:
    return [
        {
            "doctype": "Some DocType",
            "fieldname": "some_field",
            "property": "read_only",
            "property_type": "Check",
            "value": 1,
            "doctype_or_field": "DocField",
        },
    ]
```

If the feature has no property setters, omit `get_property_setters` entirely.

---

## Step 2 — Register it in the registry

Open `setup/registry.py` and add a `FeatureSpec` to `get_feature_specs()`:

```python
from .features import my_feature   # add this import at the top

# inside get_feature_specs():
FeatureSpec(
    key="my_feature",
    label="My feature customizations",
    get_custom_fields=my_feature.get_custom_fields,
    get_property_setters=my_feature.get_property_setters,   # omit if none
),
```

**Order matters** — place it after any features it depends on.

For optional features (only apply if another app is installed):

```python
FeatureSpec(
    key="my_feature",
    label="My feature customizations",
    get_custom_fields=my_feature.get_custom_fields,
    enabled=lambda: _is_installed("some_other_app"),
    is_optional=True,
)
```

---

## Step 3 — Apply on installed sites

New features are applied automatically on `after_install` for fresh installs. For already-installed sites, re-run all customizations:

```bash
bench --site <site> execute optima_payment.setup.registry.ensure_customizations
```

Or write a targeted patch if you need surgical control — see [how-to-write-a-patch.md](how-to-write-a-patch.md).

---

## Field dict reference

| Key | Required | Notes |
|-----|----------|-------|
| `fieldname` | Yes | Snake case, unique per doctype |
| `fieldtype` | Yes | `Data`, `Link`, `Currency`, `Check`, `Select`, `Date`, etc. |
| `label` | Recommended | Display label |
| `insert_after` | Recommended | Fieldname to place this field after |
| `options` | For Link/Select | Link: target doctype. Select: newline-separated options |
| `default` | No | Default value |
| `read_only` | No | `1` or `0` |
| `hidden` | No | `1` or `0` |
| `no_copy` | No | `1` to exclude from document copy |
| `depends_on` | No | JS eval expression for conditional visibility |
| `mandatory_depends_on` | No | JS eval expression for conditional mandatory |
