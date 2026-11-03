# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The branch matrix for the Time Based Overdue Limit. Nothing here writes to the database.

Rules are ``frappe._dict`` rows shaped like get_enabled_rules returns them, so no customer, group or
rule has to exist on the site. The wiring through real saves is in test_limit_integration.py.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate, getdate

from optima_payment.overdue_limit.limit import (
    BLOCK,
    BLOCK_ON_SAVE,
    BLOCK_ON_SUBMIT,
    CUSTOMER,
    CUSTOMER_GROUP,
    SAVE,
    SKIP_FLAGS,
    SUBMIT,
    WARN,
    WARN_ON_SAVE,
    Hit,
    Verdict,
    days_overdue,
    decide,
    is_exempt_document,
    is_exempt_user,
    message,
    select_rules,
)

CUSTOMER_NAME = "Al Noor Trading"
GROUP = "Retail"
PARENT_GROUP = "Commercial"
ROOT_GROUP = "All Customer Groups"
GROUP_CHAIN = [GROUP, PARENT_GROUP, ROOT_GROUP]
COMPANY = "Optima Test Company"
OTHER_COMPANY = "Optima Other Company"
EXEMPT_ROLE = "Accounts Manager"
SALES_ROLES = ["Sales User"]
INVOICE = frappe._dict(name="SINV-2026-00001", due_date="2026-10-08")


def rule(
    name="TBOL-00001",
    *,
    applies_to=CUSTOMER,
    party=CUSTOMER_NAME,
    company=None,
    action=WARN_ON_SAVE,
    threshold_days=20,
    exempt_roles=(),
):
    """A rule the way get_enabled_rules returns it."""
    return frappe._dict(
        name=name,
        applies_to=applies_to,
        party=party,
        company=company,
        action=action,
        threshold_days=threshold_days,
        exempt_roles=list(exempt_roles),
    )


def group_rule(name, group, **fields):
    return rule(name, applies_to=CUSTOMER_GROUP, party=group, **fields)


def names(rules):
    return [rule.name for rule in rules]


def hit_names(verdict):
    return [hit.rule.name for hit in verdict.hits]


class TestIsExemptDocument(FrappeTestCase):
    def test_only_credit_notes_pos_consolidations_and_system_writes_are_skipped(self):
        cases = [
            ("an ordinary invoice", 0, 0, {}, False),
            ("a Sales Order, which has neither field", None, None, {}, False),
            ("a credit note", 1, 0, {}, True),
            ("a POS consolidated invoice", 0, 1, {}, True),
            ("a skip flag set to false", 0, 0, {"in_import": False}, False),
            ("an unrelated flag", 0, 0, {"in_test": True}, False),
            *[(flag, 0, 0, {flag: True}, True) for flag in SKIP_FLAGS],
        ]
        for label, is_return, is_consolidated, flags, expected in cases:
            with self.subTest(label):
                self.assertEqual(is_exempt_document(is_return, is_consolidated, frappe._dict(flags)), expected)


class TestSelectRules(FrappeTestCase):
    def select(self, rules, company=COMPANY):
        return names(select_rules(rules, CUSTOMER_NAME, GROUP_CHAIN, company))

    def test_customer_rules_beat_group_rules(self):
        rules = [group_rule("G", GROUP), rule("C")]
        self.assertEqual(self.select(rules), ["C"])

    def test_the_nearest_group_beats_its_ancestors(self):
        rules = [group_rule("ROOT", ROOT_GROUP), group_rule("PARENT", PARENT_GROUP), group_rule("G", GROUP)]
        self.assertEqual(self.select(rules), ["G"])

    def test_an_ancestor_applies_when_nearer_tiers_have_none(self):
        rules = [group_rule("ROOT", ROOT_GROUP), group_rule("PARENT", PARENT_GROUP)]
        self.assertEqual(self.select(rules), ["PARENT"])

    def test_every_rule_of_the_tier_applies(self):
        rules = [
            rule("WARN", action=WARN_ON_SAVE, threshold_days=20),
            rule("BLOCK", action=BLOCK_ON_SUBMIT, threshold_days=30),
            group_rule("G", GROUP),
        ]
        self.assertEqual(self.select(rules), ["WARN", "BLOCK"])

    def test_a_blank_company_matches_every_company(self):
        rules = [rule("ALL"), rule("MINE", company=COMPANY)]
        self.assertEqual(self.select(rules), ["ALL", "MINE"])
        self.assertEqual(self.select(rules, company=OTHER_COMPANY), ["ALL"])

    def test_a_rule_for_another_company_neither_applies_nor_shadows_a_wider_tier(self):
        rules = [rule("C", company=OTHER_COMPANY), group_rule("G", GROUP)]
        self.assertEqual(self.select(rules), ["G"])

    def test_a_group_named_like_the_customer_is_matched_as_a_group(self):
        rules = [group_rule("G", CUSTOMER_NAME)]
        self.assertEqual(self.select(rules), [])
        self.assertEqual(names(select_rules(rules, CUSTOMER_NAME, [CUSTOMER_NAME], COMPANY)), ["G"])

    def test_a_customer_without_rules_or_group_selects_nothing(self):
        self.assertEqual(self.select([]), [])
        self.assertEqual(names(select_rules([group_rule("G", GROUP)], CUSTOMER_NAME, [], COMPANY)), [])


class TestDaysOverdue(FrappeTestCase):
    def test_days_are_counted_from_the_due_date(self):
        self.assertEqual(days_overdue("2026-10-08", "2026-11-02"), 25)
        self.assertEqual(days_overdue(getdate("2026-11-01"), getdate("2026-11-02")), 1)


class TestIsExemptUser(FrappeTestCase):
    def test_a_shared_role_exempts_only_from_a_block_rule(self):
        cases = [
            ("a shared role on a block rule", BLOCK_ON_SAVE, [EXEMPT_ROLE], {EXEMPT_ROLE}, True),
            ("a shared role on a block-on-submit rule", BLOCK_ON_SUBMIT, [EXEMPT_ROLE], {EXEMPT_ROLE}, True),
            ("no shared role", BLOCK_ON_SAVE, [EXEMPT_ROLE], set(SALES_ROLES), False),
            ("no exempt roles on the rule", BLOCK_ON_SAVE, [], {EXEMPT_ROLE}, False),
            ("a shared role on a warn rule", WARN_ON_SAVE, [EXEMPT_ROLE], {EXEMPT_ROLE}, False),
        ]
        for label, action, exempt_roles, user_roles, expected in cases:
            with self.subTest(label):
                self.assertEqual(is_exempt_user(rule(action=action, exempt_roles=exempt_roles), user_roles), expected)


class TestDecide(FrappeTestCase):
    def test_the_action_table(self):
        """Every action at both stages, for a user with and without the rule's exempt role."""
        table = [
            (WARN_ON_SAVE, SAVE, False, WARN),
            (WARN_ON_SAVE, SAVE, True, WARN),
            (WARN_ON_SAVE, SUBMIT, False, None),
            (WARN_ON_SAVE, SUBMIT, True, None),
            (BLOCK_ON_SAVE, SAVE, False, BLOCK),
            (BLOCK_ON_SAVE, SAVE, True, WARN),
            (BLOCK_ON_SAVE, SUBMIT, False, BLOCK),
            (BLOCK_ON_SAVE, SUBMIT, True, WARN),
            (BLOCK_ON_SUBMIT, SAVE, False, WARN),
            (BLOCK_ON_SUBMIT, SAVE, True, WARN),
            (BLOCK_ON_SUBMIT, SUBMIT, False, BLOCK),
            (BLOCK_ON_SUBMIT, SUBMIT, True, WARN),
        ]
        for action, stage, exempt, expected in table:
            with self.subTest(action=action, stage=stage, exempt=exempt):
                user_roles = [EXEMPT_ROLE] if exempt else SALES_ROLES
                verdict = decide([rule(action=action, exempt_roles=[EXEMPT_ROLE])], 30, user_roles, stage)
                self.assertEqual(verdict.outcome, expected)

    def test_a_rule_triggers_from_its_threshold(self):
        rules = [rule(action=BLOCK_ON_SAVE, threshold_days=20)]
        for days, expected in [(19, None), (20, BLOCK), (21, BLOCK)]:
            with self.subTest(days=days):
                self.assertEqual(decide(rules, days, SALES_ROLES, SAVE).outcome, expected)

    def test_a_block_outranks_warnings_and_leaves_them_out(self):
        rules = [rule("WARN", threshold_days=20), rule("BLOCK", action=BLOCK_ON_SAVE, threshold_days=30)]
        verdict = decide(rules, 30, SALES_ROLES, SAVE)
        self.assertEqual(verdict.outcome, BLOCK)
        self.assertEqual(hit_names(verdict), ["BLOCK"])

    def test_every_triggered_warning_is_listed(self):
        rules = [rule("WARN", threshold_days=20), rule("NOTICE", action=BLOCK_ON_SUBMIT, threshold_days=25)]
        verdict = decide(rules, 30, SALES_ROLES, SAVE)
        self.assertEqual(verdict.outcome, WARN)
        self.assertEqual(hit_names(verdict), ["WARN", "NOTICE"])

    def test_a_rule_below_its_threshold_is_left_out(self):
        rules = [rule("WARN", threshold_days=20), rule("BLOCK", action=BLOCK_ON_SAVE, threshold_days=40)]
        verdict = decide(rules, 30, SALES_ROLES, SAVE)
        self.assertEqual(verdict.outcome, WARN)
        self.assertEqual(hit_names(verdict), ["WARN"])

    def test_an_exempt_user_is_warned_and_the_hit_says_so(self):
        verdict = decide([rule(action=BLOCK_ON_SAVE, exempt_roles=[EXEMPT_ROLE])], 30, [EXEMPT_ROLE], SAVE)
        self.assertEqual(verdict.outcome, WARN)
        self.assertTrue(verdict.hits[0].exempt)

    def test_no_rules_decide_nothing(self):
        self.assertEqual(decide([], 30, SALES_ROLES, SAVE), Verdict(None, []))


class TestMessage(FrappeTestCase):
    def render(self, *hits, outcome=BLOCK):
        return message(Verdict(outcome, list(hits)), CUSTOMER_NAME, INVOICE, 25)

    def test_the_header_names_the_customer_invoice_days_and_due_date(self):
        text = self.render(Hit(rule(action=BLOCK_ON_SAVE), False))
        self.assertIn(
            f"Customer <strong>{CUSTOMER_NAME}</strong> has Sales Invoice <strong>{INVOICE.name}</strong> "
            f"overdue by <strong>25</strong> days; it was due on {formatdate(INVOICE.due_date)}.",
            text,
        )

    def test_each_action_reads_as_what_it_does(self):
        cases = [
            (WARN_ON_SAVE, "Rule <strong>TBOL-00001</strong> warns from 20 days overdue."),
            (BLOCK_ON_SAVE, "Rule <strong>TBOL-00001</strong> blocks saving and submitting from 20 days overdue."),
            (BLOCK_ON_SUBMIT, "Rule <strong>TBOL-00001</strong> blocks submitting from 20 days overdue."),
        ]
        for action, expected in cases:
            with self.subTest(action):
                self.assertIn(f"<li>{expected}</li>", self.render(Hit(rule(action=action), False)))

    def test_a_blocked_user_is_told_which_roles_can_continue(self):
        text = self.render(Hit(rule(action=BLOCK_ON_SAVE, exempt_roles=[EXEMPT_ROLE, "System Manager"]), False))
        self.assertIn("Roles that can continue: Accounts Manager, System Manager.", text)

    def test_an_exempt_user_is_told_their_role_lets_them_continue(self):
        text = self.render(Hit(rule(action=BLOCK_ON_SAVE, exempt_roles=[EXEMPT_ROLE]), True), outcome=WARN)
        self.assertIn("Your role lets you continue.", text)
        self.assertNotIn("Roles that can continue", text)

    def test_a_warn_rule_lists_no_roles(self):
        text = self.render(Hit(rule(action=WARN_ON_SAVE, exempt_roles=[EXEMPT_ROLE]), False), outcome=WARN)
        self.assertNotIn("Roles that can continue", text)

    def test_every_hit_gets_its_own_line(self):
        text = self.render(Hit(rule("FIRST"), False), Hit(rule("SECOND"), False), outcome=WARN)
        self.assertEqual(text.count("<li>"), 2)
