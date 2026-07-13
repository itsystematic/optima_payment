# Access Control — Optima Roles & Permissions

How Optima Payment seeds its two convenience roles and their permissions, and why this moved
from JSON fixtures to code.

Source: [`setup/permissions.py`](../../optima_payment/setup/permissions.py).

---

## The two roles

| Role | Intent |
|------|--------|
| `Optima Payment User` | Read / data-entry access across HR, banking, and accounting doctypes. |
| `Optima Payment Manager` | The same as User, plus create / delete / submit / cancel / amend where relevant. |

They come with a bundle of **Custom DocPerms** granting access to ~27 standard doctypes —
`Employee`, `Expense Claim`, `Bank`, `Bank Account`, `Cost Center`, `Project`, `Sales Invoice`,
`Purchase Invoice`, `Cheque Deposit Slip`, and more. The grid lives in `setup/permissions.py`,
split in two because **HRMS is optional** on this app:

- `ROLE_PERMISSIONS` — Frappe/ERPNext doctypes, applied on every install.
- `HRMS_ROLE_PERMISSIONS` — HRMS-owned doctypes (`Expense Claim`, `Expense Claim Type`,
  `Employee Advance`, `Employee Grade`, `Employment Type`, `Job Applicant`,
  `Salary Structure Assignment`), applied only when HRMS is on the site. Seeding a permission
  loads the DocType (`add_permission` / `validate_permissions_for_doctype` both
  `frappe.get_doc("DocType", …)`), so an ungated row would crash the install on a
  non-HRMS site with `DoesNotExistError`.

## Why they exist

They are a **legacy permission preset**, inherited from the old `cheque` app. An administrator
assigns one of these roles to a staff member to hand them a ready-made permission bundle in one
click, instead of ticking dozens of Role Permission Manager rows by hand.

Important: they are **not wired into this app's code or its own doctype permissions**. Optima
Payment's own doctypes (Letter of Credit, Bank Guarantee-BG, Optima Payment Setting, …) grant
access to standard ERPNext roles (Accounts User/Manager, System Manager). So this bundle is
**pure admin convenience**, not a functional dependency — the app works without it.

## Why code instead of a JSON fixture

Historically the roles and their docperms were seeded from `files/role.json` and
`files/custom_docperm.json` via `import_doc` at install. Expressing them in code instead:

- **Reversible** — removed cleanly on uninstall (the JSON import never was).
- **Reviewable** — the permission grid is greppable and diffs cleanly, instead of hiding in
  900 lines of JSON (where the original `Manger` typo went unnoticed for a long time).
- **Co-located** — access control now lives beside the rest of the `setup/` framework.

Print formats (`files/print_format.json`) deliberately **stayed** a JSON import: 75 KB of opaque
bank HTML belongs in data, not Python. See [architecture.md](architecture.md#three-kinds-of-seeded-state-know-the-difference).

## Lifecycle

- **Install** (`install.after_install` → `apply_access_control`): upserts the roles
  (`ensure_roles`) then applies the core permission grid (`ensure_permissions`) via Frappe's
  `add_permission` / `update_permission_property`; the HRMS grid is added in the same run
  **only if HRMS is already installed**. Idempotent — safe to re-run.
- **HRMS installed later** (`hooks.after_app_install` → `install.after_app_install`): Frappe
  fires this hook on every installed app whenever *any* app is installed on the site, passing
  the new app's name. Our handler no-ops unless the name is `hrms`, then applies the HRMS
  custom fields (`registry.ensure_hrms_customizations`) and the HRMS permission grid
  (`apply_hrms_access_control`). Together with the install-time check, both install orderings
  are covered.
- **Migrate**: **not** re-applied. Like the print-format seed, admins may tune per-site
  permissions and a later `bench migrate` must not overwrite them.
- **Uninstall** (`uninstall.before_uninstall` → `remove_access_control`): deletes the Custom
  DocPerm rows for the two roles across both grids (restoring default perms), then deletes each
  role **only if no user is still assigned it** — an assigned role is kept with a warning so
  nobody loses access.
- **HRMS uninstalled** (while Optima Payment stays): nothing to do on our side — deleting a
  DocType makes Frappe drop its `Custom DocPerm` and `Custom Field` rows (`DocType.on_trash`),
  and both `ensure_permissions` and `remove_access_control` skip doctypes missing from the site.

## The `Manger → Manager` rename

The role shipped misspelled as `Optima Payment Manger`. Fresh installs now get the correct
`Optima Payment Manager` from code. Already-installed sites are fixed by the patch
[`patches/rename_optima_payment_manger_role.py`](../../optima_payment/patches/rename_optima_payment_manger_role.py),
which renames the Role so existing user assignments and Custom DocPerms follow the link.

## How to change what the roles can do

Edit `ROLE_PERMISSIONS` — or `HRMS_ROLE_PERMISSIONS` for an HRMS doctype — in
`setup/permissions.py` (add a doctype, or add/remove a ptype for a role), then re-run on a
dev site:

```bash
bench --site <site> console
```
```python
from optima_payment.setup.permissions import apply_access_control
apply_access_control()
```

`add_permission` only ever *adds* — if you **remove** a doctype or narrow a ptype in the grid,
existing sites keep the old rule until you write a patch (or re-run `remove_access_control`
then `apply_access_control`). For a rename or removal on installed sites, ship a patch — see
[how-to-write-a-patch.md](how-to-write-a-patch.md).
