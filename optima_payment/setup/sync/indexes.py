"""Create declared indexes and drop them on uninstall.

An index has no Customize Form row and no ownership flag, so there is nothing to keep: a declared
index missing from its table is created, and uninstall drops it. Frappe's schema sync never drops a
multi-column index, so it survives migrates.
"""

from __future__ import annotations

import frappe

from .report import Change


def sync(declared: dict[str, list[list[str]]], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    for doctype, indexes in declared.items():
        if not frappe.db.exists("DocType", doctype):
            changes.append(Change("missing", doctype, "doctype is not on this site"))
            continue

        for fields in indexes:
            if _exists(doctype, fields):
                continue
            changes.append(Change("create", _target(doctype, fields), _columns(fields)))
            if not dry_run:
                frappe.db.add_index(doctype, fields)

    return changes


def remove(declared: dict[str, list[list[str]]], dry_run: bool) -> list[Change]:
    changes: list[Change] = []
    for doctype, indexes in declared.items():
        if not frappe.db.exists("DocType", doctype):
            continue

        for fields in indexes:
            if not _exists(doctype, fields):
                continue
            changes.append(Change("remove", _target(doctype, fields), _columns(fields)))
            if not dry_run:
                index_name = frappe.db.get_index_name(fields)
                frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP INDEX `{index_name}`")

    return changes


def _exists(doctype: str, fields: list[str]) -> bool:
    return bool(frappe.db.has_index(f"tab{doctype}", frappe.db.get_index_name(fields)))


def _target(doctype: str, fields: list[str]) -> str:
    return f"{doctype}.{frappe.db.get_index_name(fields)}"


def _columns(fields: list[str]) -> str:
    return f"({', '.join(fields)})"
