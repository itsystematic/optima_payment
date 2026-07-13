"""Access-control seed for Optima Payment: the two Optima roles and their permissions.

## What this is

Optima Payment ships two convenience roles and a bundle of Custom DocPerms that grant them
access to standard HR/banking/accounting doctypes (Employee, Bank, Purchase Invoice, Cost
Center, Cheque Deposit Slip, …):

- ``Optima Payment User``    — read / data-entry access.
- ``Optima Payment Manager`` — the same, plus create / delete / submit / cancel / amend.

## Why these exist

They are a **legacy permission preset**, inherited from the old ``cheque`` app. An
administrator assigns one of these roles to a staff member to hand them a ready-made bundle
of cross-cutting permissions in one click, instead of ticking dozens of Role Permission
Manager rows by hand.

## Why this lives in code (not a fixture / JSON import)

Historically these were seeded from ``files/role.json`` + ``files/custom_docperm.json`` via
``import_doc`` at install time. Expressing them in code instead keeps them:

- **reversible** — :func:`remove_access_control` cleans them up on uninstall, matching the
  rest of the setup framework (custom fields / property setters);
- **reviewable** — the permission grid is greppable and diffs cleanly;
- **co-located** — access control lives beside the rest of ``setup/``.

Print formats stayed a JSON ``import_doc`` seed (see ``standard_data.py``): 75 KB of opaque
bank HTML belongs in data, not Python.

## Lifecycle

- Applied **on install only** (``install.after_install``). Like the print-format seed, admins
  may tune per-site permissions afterwards without a later ``bench migrate`` overwriting them.
- The grid is split in two: :data:`ROLE_PERMISSIONS` (Frappe/ERPNext doctypes, always applied)
  and :data:`HRMS_ROLE_PERMISSIONS` (HRMS-owned doctypes). HRMS is **optional** — its grid is
  applied at install only when HRMS is already on the site, and via
  ``hooks.after_app_install`` → :func:`apply_hrms_access_control` when HRMS is installed later.
- Removed on uninstall (``uninstall.before_uninstall``): the Custom DocPerm rows are dropped,
  and each role is deleted **only if no user is still assigned it**. (If HRMS is uninstalled
  first, Frappe deletes its doctypes' Custom DocPerm rows itself — DocType.on_trash.)

To change what the roles can do, edit :data:`ROLE_PERMISSIONS` (or :data:`HRMS_ROLE_PERMISSIONS`
for HRMS doctypes) below. To rename a role on already-installed sites, ship a patch (see
``patches/rename_optima_payment_manger_role.py``).
"""

from __future__ import annotations

import click
import frappe
from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
from frappe.permissions import add_permission, update_permission_property

from .runner import run_setup_steps

USER_ROLE = "Optima Payment User"
MANAGER_ROLE = "Optima Payment Manager"

# Role records to upsert. Attributes mirror the retired files/role.json.
OPTIMA_ROLES: list[dict] = [
    {"role_name": USER_ROLE, "desk_access": 1, "is_custom": 0},
    {"role_name": MANAGER_ROLE, "desk_access": 1, "is_custom": 0},
]

# Faithful permission grid, transcribed from the retired files/custom_docperm.json.
# Shape: {doctype: {role: [enabled ptypes]}}. All rows are permlevel 0, if_owner 0.
# `User` is read/data-entry; `Manager` adds create/delete/submit/cancel/amend where relevant.
# HRMS-owned doctypes live in HRMS_ROLE_PERMISSIONS below — HRMS is optional.
ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "Employee": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "share", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "share", "report"],
    },
    "Department": {
        USER_ROLE: ["select", "read", "write", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
    },
    "Designation": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
    },
    "Branch": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
    },
    "Holiday List": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "email", "export", "report"],
    },
    "Bank": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Sales Taxes and Charges Template": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
    },
    "Purchase Taxes and Charges Template": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
    },
    "Project": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Cost Center": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Bank Account": {
        USER_ROLE: ["select", "read", "write", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Supplier": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Supplier Group": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Customer": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Customer Group": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Sales Invoice": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "share", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "share", "report"],
    },
    "Purchase Invoice": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "share", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "report"],
    },
    "Optima Payment Setting": {
        USER_ROLE: ["read", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Cheque Deposit Slip": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "import", "share", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "import", "share", "report"],
    },
    "Report": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "share", "report"],
        MANAGER_ROLE: ["read", "write", "create", "print", "email", "export", "share", "report"],
    },
}

# HRMS-owned doctypes (same shape as ROLE_PERMISSIONS). Seeding a permission loads the
# DocType doc, so these rows crash on a site without HRMS — they are applied only when
# HRMS is installed: at install time if already present, else via hooks.after_app_install.
HRMS_ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "Expense Claim": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "share", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "share", "report"],
    },
    "Expense Claim Type": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Employee Advance": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "report"],
    },
    "Employee Grade": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Employment Type": {
        USER_ROLE: ["select", "read", "write", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "print", "email", "export", "report"],
    },
    "Job Applicant": {
        USER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "print", "email", "export", "report"],
    },
    "Salary Structure Assignment": {
        USER_ROLE: ["select", "read", "write", "create", "submit", "print", "email", "export", "report"],
        MANAGER_ROLE: ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "export", "report"],
    },
}


def apply_access_control() -> None:
    """Create the Optima roles and their Custom DocPerms (install-time seed)."""
    steps = [
        ("Create Optima Payment roles", ensure_roles),
        ("Apply Optima Payment permissions", lambda: ensure_permissions(ROLE_PERMISSIONS)),
    ]
    if "hrms" in frappe.get_installed_apps():
        steps.append(
            ("Apply Optima Payment HRMS permissions", lambda: ensure_permissions(HRMS_ROLE_PERMISSIONS))
        )
    run_setup_steps(steps, section_label="Optima Payment access control")


def apply_hrms_access_control() -> None:
    """Grant the Optima roles their HRMS permissions.

    Entry point for ``hooks.after_app_install`` when HRMS is installed on a site that
    already has Optima Payment. Idempotent, like the install-time seed.
    """
    run_setup_steps(
        [
            ("Create Optima Payment roles", ensure_roles),
            ("Apply Optima Payment HRMS permissions", lambda: ensure_permissions(HRMS_ROLE_PERMISSIONS)),
        ],
        section_label="Optima Payment HRMS access control",
    )


def ensure_roles() -> None:
    """Idempotently upsert the Optima Payment roles."""
    for role in OPTIMA_ROLES:
        role_name = role["role_name"]
        if frappe.db.exists("Role", role_name):
            click.secho(f"Role already exists: {role_name}", fg="green")
            continue

        frappe.get_doc({"doctype": "Role", **role}).insert(ignore_if_duplicate=True)
        click.secho(f"Created role: {role_name}", fg="green")


def ensure_permissions(grid: dict[str, dict[str, list[str]]]) -> None:
    """Grant each Optima role its permissions on every doctype in the grid."""
    for doctype, roles in grid.items():
        # add_permission / validate_permissions_for_doctype load the DocType and raise
        # DoesNotExistError on a missing one (e.g. an HRMS doctype without HRMS).
        if not frappe.db.exists("DocType", doctype):
            click.secho(f"Skipping permissions for missing DocType: {doctype}", fg="yellow")
            continue

        for role, ptypes in roles.items():
            # add_permission creates the base (read) rule and is a no-op if it already exists.
            add_permission(doctype, role, 0)
            for ptype in ptypes:
                update_permission_property(doctype, role, 0, ptype, 1, validate=False)
        validate_permissions_for_doctype(doctype)
        click.secho(f"Applied Optima permissions on: {doctype}", fg="green")


def remove_access_control() -> None:
    """Remove Optima Custom DocPerms; delete each role only if no user still has it."""
    removed_perms = _remove_permissions()
    click.secho(f"Removed {removed_perms} Optima permission rows", fg="green")
    _remove_unassigned_roles()


def _remove_permissions() -> int:
    """Delete Custom DocPerm rows for the Optima roles and revalidate touched doctypes."""
    removed = 0
    for doctype in (*ROLE_PERMISSIONS, *HRMS_ROLE_PERMISSIONS):
        names = frappe.get_all(
            "Custom DocPerm",
            filters={"parent": doctype, "role": ["in", [USER_ROLE, MANAGER_ROLE]]},
            pluck="name",
        )
        for name in names:
            frappe.delete_doc("Custom DocPerm", name, force=True)
            removed += 1

        # Revalidation loads the DocType; skip it for doctypes no longer on the site
        # (an uninstalled HRMS already dropped its rows via DocType.on_trash anyway).
        if names and frappe.db.exists("DocType", doctype):
            validate_permissions_for_doctype(doctype)
            frappe.clear_cache(doctype=doctype)

    return removed


def _remove_unassigned_roles() -> None:
    """Delete each Optima role when unused; keep and warn if a user is still assigned it."""
    for role in (USER_ROLE, MANAGER_ROLE):
        if not frappe.db.exists("Role", role):
            continue

        if frappe.db.exists("Has Role", {"role": role}):
            click.secho(
                f"Role '{role}' is still assigned to users; leaving it in place.",
                fg="yellow",
            )
            continue

        frappe.delete_doc("Role", role, force=True)
        click.secho(f"Deleted unused role: {role}", fg="green")
