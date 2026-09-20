# How to Alter an Existing Feature

Every change below is two steps: **edit the declaration**, then **ship one patch that calls
`sync()`**. The patch is what carries the change to sites that are already installed —
[how-to-write-a-patch.md](how-to-write-a-patch.md).

---

## Add a field to an existing feature

Add the dict to the doctype's list in the feature module, then ship a patch. `sync()` creates the
new field and leaves everything else alone.

If a site already has a field with that fieldname at flag 0, the sync reports `keep` and does not
touch it: the site's version stands.

---

## Change a property (label, default, depends_on, hidden…)

Edit the field dict, then ship a patch.

What each site gets depends on who owns the row:

| On the site | Result |
|-------------|--------|
| the app's Custom Field row (flag 1) | `update` — the new value applies |
| the client edited that property in Customize Form | `keep` — their value stands, and the app's new value is ignored on that site |

That second row is the intended trade-off: the client's choice outranks a later app default. If a
change is a correctness fix that must reach every site, say so in the patch docstring and follow up
with the affected sites — the report names them.

---

## Change a declared property setter

Same as above: edit `get_property_setters()`, ship a patch. `sync()` updates the row only while it
is still app-owned (flag 1).

---

## Remove a property setter

1. Delete it from `get_property_setters()`.
2. Ship a patch that deletes the row **by its full key**:

```python
frappe.db.delete(
    "Property Setter",
    {"doc_type": "Payment Entry", "field_name": "payee_name", "property": "hidden"},
)
```

> **Never match on doctype + property alone.** That also matches the client's row for other fields.
> A cleanup that did this is what wiped the Payment Entry layout on live sites.

Dropping the declaration alone changes nothing on existing sites; it only stops fresh installs from
creating it.

---

## Rename a field

A rename needs a patch that creates, copies, then deletes — the order matters. See the rename
pattern in [how-to-write-a-patch.md](how-to-write-a-patch.md). Update the declaration in the same
commit so fresh installs use the new name.

---

## Change a fieldtype

Not in place, ever. `sync()` reports a `conflict` and writes nothing, because rewriting the column
can lose data. Declare a new fieldname, migrate the data in a patch, then remove the old field.

---

## Remove a field

1. Remove it from `get_custom_fields()`.
2. Ship a patch that deletes the Custom Field row.

Deleting the field also removes every property setter on it, including the client's. Frappe leaves
the column and its data in the table.

---

## Change the form layout

The app does not own form layouts. `field_order` is written once at install, only if the site has
none, and never touched again — [questions-and-answers.md](questions-and-answers.md) explains why.

To move one of the app's own fields, change its `insert_after` in the declaration and ship a patch.
Sites where the client has arranged that form keep their arrangement.
