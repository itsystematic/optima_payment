# Setup — Questions and Answers

Short answers for developers working on the customization setup. For the full model, see
[architecture.md](architecture.md).

---

## What is a "key", and why does it matter?

A key identifies a row. The value is not part of it.

| Record | Key | Example row name |
|--------|-----|------------------|
| Custom Field | doctype + fieldname | `Payment Entry-payee_name` |
| Property Setter | doctype + field (or grid row) + property | `Payment Entry-payee_name-hidden` |

Frappe deletes any existing Property Setter with the same key when a new one is inserted. So two
parties can never "both" hold a key — the last writer owns it, and ownership is what the flag
records.

## What do flag 0 and flag 1 mean?

`is_system_generated` on the row:

- **1** — written by code. The app owns it and the sync may update it.
- **0** — written by Customize Form. The site owns it and the sync never changes it.

## The client changed a field the app declares. What happens on the next migrate?

It depends on what they changed:

| They changed | Frappe writes | The sync then |
|--------------|---------------|---------------|
| a property of one of **our custom fields** (hidden, label, position…) | a Property Setter at flag 0, leaving our Custom Field row alone | updates our row if code changed, and leaves their setter alone, so their change still wins |
| a property the app **also declares** on a standard field | replaces our flag-1 Property Setter with a flag-0 one | reports `keep` and never touches it again |
| the **form layout** (dragging fields) | one `field_order` row for the whole doctype | never syncs `field_order` at all |

In all three cases the client's change survives every future migrate.

## Why is `field_order` special?

Because it is one row holding the **entire** form order for a doctype, not a per-field setting.
Every time the client drags a field, Customize Form rewrites that whole value. If the app wrote its
own `field_order`, it would replace the client's full layout — which is exactly what used to wipe
the Payment Entry layout on client sites.

So: `field_order` is written **only at install, only when the site has no `field_order` row yet**
(`apply_starting_field_orders()`), and never compared or updated afterwards.

Positions for individual fields still work: the app declares `insert_after`, and Frappe's Meta
honours a per-field `insert_after` property setter, which is how adoption preserved site positions.

## Does the sync ever touch customizations the client made themselves?

No. Two separate reasons:

1. **The sync only looks at declared keys.** It reads the feature declarations, then looks up
   exactly those rows. A field the client added (Frappe names these `custom_…`, and the fieldname
   is read-only in the UI) or a property they set on a field the app never declared is never read,
   never flagged and never deleted.
2. **The sync never adopts.** Moving a row from flag 0 to flag 1 happens only in the one-time patch
   `patches/adopt_existing_customizations.py`, which exists for customizations created before
   ownership was tracked. It is deliberately not part of `setup/sync/`, so no later patch can run it
   again against something a client made afterwards.

There is a test for exactly this: a client custom field and a client property setter must come
through adoption, sync and uninstall byte-identical
(`tests/test_customization_sync.py::TestClientCustomizationsAreNeverTouched`).

## What does uninstall remove, and what does it keep?

```
every declared Custom Field            → removed (Frappe also removes every setter on that field)
declared Property Setter, flag 1       → removed
declared Property Setter, flag 0
   ├── value equals the declaration    → removed (an old import wrote it, not the client)
   └── value differs                   → kept
anything the app never declared        → untouched
```

Columns are not dropped: Frappe leaves the data in the table, so an accidental uninstall followed by
a reinstall does not lose values.

## How do I ship a change to sites that are already installed?

Edit the feature module, then add **one patch per change** whose docstring says what it does and
whose body calls `sync()`. That is the whole workflow —
[how-to-write-a-patch.md](how-to-write-a-patch.md).

Why not just re-run everything on every migrate? Because "re-apply all" is what overwrites client
work. The app only touches a site when a patch says so, and even then only rows it owns.

## Can I rename a field, or change its fieldtype?

- **Rename:** yes, with a patch. Create the new field first (`sync()`), copy the data, then delete
  the old Custom Field row. `patches/rename_lc_account_to_providing_and_add_receiving.py` is the
  worked example.
- **Fieldtype:** never in place. The sync reports a `conflict` and changes nothing, because changing
  a fieldtype rewrites the column and can lose data. Declare a new fieldname, migrate the data in a
  patch, then remove the old field.

## Two features declare the same field. Is that a problem?

Only if they disagree. Identical declarations merge silently. The same key declared with two
different values raises `DeclarationConflict` and the sync stops before writing anything — fix the
declarations.

## How do I read the report?

```
Optima Payment customization sync (applied): 3 item(s)
   create   Bank Account.providing_letter_of_credit_account
   update   Payment Entry.payee_name  label: 'Payee' -> 'Payee Name'
   keep     Payment Entry-taxes-depends_on  client value '', code value "eval: …"
```

| Action | What it tells you |
|--------|-------------------|
| `create` | the row was missing; the app created it |
| `update` | an app-owned row drifted from code and was set back |
| `keep` | the site owns this row; nothing was written |
| `conflict` | needs a human: a fieldtype differs, or two rows share one key |
| `missing` | the doctype is not installed here (e.g. HRMS fields without HRMS) |
| `remove` | uninstall deleted an app-owned row |
| `adopt` | the one-time patch moved a row to flag 1 |

A long run of `keep` lines on an old site is normal: those are rows the app has not adopted and
will not touch.

## How do I check that a migrate did not damage the forms?

Snapshot before, compare after — see [how-to-check-a-migrate.md](how-to-check-a-migrate.md). The
snapshot covers every doctype on the site that carries a custom field or property setter, whichever
app put it there, so it also catches damage done by another app during the same migrate.

## A field I declared is not on the site. Why?

Check the report:

- `missing` — the doctype is not installed (an HRMS field on a site without HRMS).
- `keep` — a flag-0 row already exists under that key, so the site's version stands.
- nothing at all — no patch has carried the change to that site yet. Adding a declaration only
  affects fresh installs until a patch calls `sync()`.

## Is the sync safe to run twice?

Yes. It compares before writing, so a second run reports nothing to do. A migrate that runs twice
changes nothing the second time.

One caveat for patch authors: **creating or updating a custom field commits.** Frappe alters the
table, and MariaDB commits DDL, so that part of a patch cannot be rolled back. Do the reversible
work (data copies, row deletes) around it deliberately, and take a backup before migrating a client
site.
