# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Time Based Overdue Limit: warn about or block a Sales Invoice or Sales Order whose customer has
a Sales Invoice unpaid too long past its due date.

The age that counts is that of the customer's oldest overdue invoice in the document's company. Only
the most specific tier of rules applies: the customer's own, else its group's, else the nearest
ancestor group's. Each action is checked at its own hook: Warn on Save at validate, Block on Save at
before_save, Block on Submit at before_submit.

Branching lives in the DECISIONS functions, which take plain rows and return values.
"""

from collections import namedtuple

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

RULE = "Time Based Overdue Limit"
EXEMPT_ROLE = "Time Based Overdue Limit Exempt Role"
CUSTOMER = "Customer"
CUSTOMER_GROUP = "Customer Group"

WARN_ON_SAVE = "Warn on Save"
BLOCK_ON_SAVE = "Block on Save"
BLOCK_ON_SUBMIT = "Block on Submit"

WARN = "warn"
BLOCK = "block"

SKIP_FLAGS = ("in_migrate", "in_patch", "in_install", "in_import")
OVERDUE_STATUSES = ("Overdue", "Overdue and Discounted")

Hit = namedtuple("Hit", ["rule", "exempt"])
Verdict = namedtuple("Verdict", ["outcome", "hits"])


class OverdueLimitError(frappe.ValidationError):
    pass


# ====================================================================================================
# DECISIONS
# Pure: no database.


def is_exempt_document(is_return, is_consolidated, flags) -> bool:
    """Credit notes only lower what the customer owes, and blocking a POS consolidated invoice would
    break POS Closing. Nothing written by migrate, a patch, an install or a data import is checked."""
    return bool(is_return or is_consolidated or any(flags.get(flag) for flag in SKIP_FLAGS))


def select_rules(rules: list, customer: str, group_chain: list[str], company: str, action: str) -> list:
    """The ``action`` rules governing ``customer`` in ``company``.

    The tier is the first that has any rule, whatever its action, so a customer's Warn on Save rule
    still shadows its group's Block on Save rule. ``group_chain`` is the customer's group followed by
    its ancestors, nearest first. A rule with no company applies in every company, and a rule for
    another company does not shadow a wider tier.
    """
    in_company = [rule for rule in rules if not rule.company or rule.company == company]
    tiers = [(CUSTOMER, customer)] + [(CUSTOMER_GROUP, group) for group in group_chain]
    for applies_to, party in tiers:
        tier = [rule for rule in in_company if rule.applies_to == applies_to and rule.party == party]
        if tier:
            return [rule for rule in tier if rule.action == action]
    return []


def days_overdue(due_date, today) -> int:
    return (getdate(today) - getdate(due_date)).days


def is_exempt_user(rule, user_roles: set) -> bool:
    """Exempt roles only turn a block into a warning, so they mean nothing on a Warn on Save rule."""
    return rule.action != WARN_ON_SAVE and bool(user_roles & set(rule.exempt_roles))


def decide(rules: list, days: int, user_roles) -> Verdict:
    """What ``rules``, all of one action, do once the customer is ``days`` overdue.

    A rule triggers once ``days`` reaches its ``threshold_days``. Warn on Save warns. A block rule
    blocks, but only warns a user holding one of its exempt roles. A block outranks warnings, which its
    message then leaves out.
    """
    roles = set(user_roles)
    hits = {BLOCK: [], WARN: []}
    for rule in rules:
        if days < rule.threshold_days:
            continue
        exempt = is_exempt_user(rule, roles)
        outcome = WARN if rule.action == WARN_ON_SAVE or exempt else BLOCK
        hits[outcome].append(Hit(rule, exempt))

    for outcome in (BLOCK, WARN):
        if hits[outcome]:
            return Verdict(outcome, hits[outcome])
    return Verdict(None, [])


# ====================================================================================================
# MESSAGES


def message(verdict: Verdict, customer: str, invoice, days: int) -> str:
    header = _("Customer {0} has Sales Invoice {1} overdue by {2} days; it was due on {3}.").format(
        frappe.bold(customer), frappe.bold(invoice.name), frappe.bold(days), formatdate(invoice.due_date)
    )
    lines = "".join(f"<li>{_hit_line(hit)}</li>" for hit in verdict.hits)
    return f"{header}<ul>{lines}</ul>"


def _hit_line(hit: Hit) -> str:
    rule = hit.rule
    line = _("Rule {0} ({1}) applies from {2} days overdue.").format(
        frappe.bold(rule.name), _(rule.action), rule.threshold_days
    )
    if hit.exempt:
        return f"{line} {_('Your role lets you continue.')}"
    if rule.action != WARN_ON_SAVE and rule.exempt_roles:
        roles = ", ".join(_(role) for role in rule.exempt_roles)
        return f"{line} {_('Roles that can continue: {0}.').format(roles)}"
    return line


# ====================================================================================================
# CHECK


def check(doc: Document, action: str) -> None:
    """Warns about or blocks a Sales Invoice or Sales Order as its customer's ``action`` rules say."""
    if not doc.customer or is_exempt_document(doc.get("is_return"), doc.get("is_consolidated"), frappe.flags):
        return

    rules = get_rules(doc.customer, doc.company, action)
    if not rules:
        return

    invoice = get_oldest_overdue_invoice(doc.customer, doc.company)
    if not invoice:
        return

    days = days_overdue(invoice.due_date, getdate())
    verdict = decide(rules, days, frappe.get_roles())
    if not verdict.outcome:
        return

    text = message(verdict, doc.customer, invoice, days)
    if verdict.outcome == BLOCK:
        frappe.throw(text, OverdueLimitError, title=_("Overdue Limit"))
    frappe.msgprint(text, title=_("Overdue Limit"), indicator="orange")


# ====================================================================================================
# QUERIES


def get_rules(customer: str, company: str, action: str) -> list:
    group_chain = get_group_chain(frappe.db.get_value(CUSTOMER, customer, "customer_group"))
    return select_rules(get_enabled_rules([customer, *group_chain]), customer, group_chain, company, action)


def get_group_chain(customer_group: str | None) -> list[str]:
    """``customer_group`` and its ancestors, nearest first.

    Read lft and rgt uncached: adding a group renumbers the rest of the tree in SQL, which leaves
    their cached documents stale.
    """
    if not customer_group:
        return []

    lft, rgt = frappe.db.get_value(CUSTOMER_GROUP, customer_group, ["lft", "rgt"])
    return frappe.get_all(
        CUSTOMER_GROUP,
        filters={"lft": ("<=", lft), "rgt": (">=", rgt)},
        order_by="lft desc",
        pluck="name",
    )


def get_enabled_rules(parties: list[str]) -> list:
    """The enabled rules naming any of ``parties``, each with its ``exempt_roles`` as a list."""
    rules = frappe.get_all(
        RULE,
        filters={"enabled": 1, "party": ("in", parties)},
        fields=["name", "applies_to", "party", "company", "action", "threshold_days"],
        order_by="threshold_days asc, name asc",
    )
    if not rules:
        return []

    roles = frappe.get_all(
        EXEMPT_ROLE,
        filters={"parenttype": RULE, "parent": ("in", [rule.name for rule in rules])},
        fields=["parent", "role"],
    )
    for rule in rules:
        rule.exempt_roles = [row.role for row in roles if row.parent == rule.name]
    return rules


def get_oldest_overdue_invoice(customer: str, company: str):
    """The Sales Invoice ERPNext marks Overdue whose due date is furthest past, or None.

    ERPNext's daily ``update_invoice_status`` job is what turns an Unpaid invoice Overdue, so on a
    site whose scheduler is off, no invoice counts.
    """
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "company": company, "status": ("in", OVERDUE_STATUSES)},
        fields=["name", "due_date"],
        order_by="due_date asc, name asc",
        limit=1,
    )
    return invoices[0] if invoices else None
