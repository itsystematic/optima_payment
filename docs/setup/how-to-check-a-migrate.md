# How to Check a Migrate for Layout Damage

`setup/form_snapshot.py` records how every customized form looks, so you can prove a migrate
changed nothing the client would notice.

It covers **every doctype on the site that carries a custom field or a property setter**, whichever
app put it there — so it also catches damage done by another app during the same migrate.

---

## Step 1 — Snapshot before

```bash
bench --site <site> backup
bench --site <site> execute optima_payment.setup.form_snapshot.save
```

The file lands in `<site>/private/files/optima-form-snapshot.json`. Pass your own path with
`--kwargs "{'path': '/tmp/before.json'}"`.

It records, per doctype: the field order, every Customize Form property of every field, the
doctype-level properties including `field_order`, plus a count of custom fields and property setters
by owner.

---

## Step 2 — Migrate

```bash
bench --site <site> migrate
```

---

## Step 3 — Compare

```bash
bench --site <site> execute optima_payment.setup.form_snapshot.diff
```

```
Comparing 133 forms with the snapshot taken at 2026-09-20 12:23:39
No differences.
```

Anything that did change is listed one per line:

```
4 difference(s):
   Payment Entry: field order changed
   Payment Entry.is_system_generated: field gone
   Payment Entry.party.hidden: 0 -> 1
   Payment Entry.field_order: None -> '["title", "amended_from", …
```

---

## Reading the result

| Line | Means |
|------|-------|
| `<doctype>: field order changed` | the form order moved — check whether a `field_order` row was written or deleted |
| `<doctype>.<field>: field gone` | a Custom Field was deleted |
| `<doctype>.<field>: field added` | a new field appeared, which is expected when a patch adds one |
| `<doctype>.<field>.<property>: a -> b` | one property changed |
| `<doctype>: newly customized` | the doctype had no customization when the snapshot was taken |

An intended change shows up here too: after a patch that adds fields, expect `field added` lines
and nothing else.

---

## In code

```python
from optima_payment.setup import form_snapshot

before = form_snapshot.snapshot(["Payment Entry"])
...
differences = form_snapshot.compare(before, form_snapshot.snapshot(["Payment Entry"]))
```

`snapshot()` takes an optional list of doctypes; with none it covers every customized doctype.
