# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The Time Based Overdue Limit's decisions, on plain rows. Nothing here writes to the database.

Only what a plausible edit could break is here: which tier of rules applies, the action table, how
several triggered rules combine, the day a rule starts, what the message tells the user about
exemption, and the documents never checked, which no integration test reaches for POS. The wiring is
in test_limit_integration.py.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.overdue_limit.limit import (
    BLOCK,
    BLOCK_ON_SAVE,
    BLOCK_ON_SUBMIT,
    CUSTOMER,
    CUSTOMER_GROUP,
    SAVE,
    SUBMIT,
    WARN,
    WARN_ON_SAVE,
    days_overdue,
    decide,
    is_exempt_document,
    message,
    rule_outcome,
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


def hit_names(verdict):
    return [hit.rule.name for hit in verdict.hits]


class TestIsExemptDocument(FrappeTestCase):
    def test_credit_notes_pos_consolidations_and_system_writes_are_never_checked(self):
        """Flags by their literal names: looping over SKIP_FLAGS cannot catch a misspelt one."""
        self.assertFalse(is_exempt_document(None, None, frappe._dict()))
        self.assertTrue(is_exempt_document(1, 0, frappe._dict()))
        self.assertTrue(is_exempt_document(0, 1, frappe._dict()))
        for flag in ("in_migrate", "in_patch", "in_install", "in_import"):
            with self.subTest(flag):
                self.assertTrue(is_exempt_document(0, 0, frappe._dict({flag: True})))


class TestSelectRules(FrappeTestCase):
    def select(self, rules, company=COMPANY):
        return [rule.name for rule in select_rules(rules, CUSTOMER_NAME, GROUP_CHAIN, company)]

    def test_the_nearest_tier_with_a_rule_wins(self):
        customer, group, parent, root = (
            rule("CUSTOMER"),
            group_rule("GROUP", GROUP),
            group_rule("PARENT", PARENT_GROUP),
            group_rule("ROOT", ROOT_GROUP),
        )
        # Furthest first, so the order of the rows cannot be what picks the winner.
        cases = [
            ([root, parent, group, customer], "CUSTOMER"),
            ([root, parent, group], "GROUP"),
            ([root, parent], "PARENT"),
        ]
        for rules, winner in cases:
            with self.subTest(winner):
                self.assertEqual(self.select(rules), [winner])

    def test_every_rule_of_the_winning_tier_applies(self):
        rules = [rule("WARN"), rule("BLOCK", action=BLOCK_ON_SAVE), group_rule("GROUP", GROUP)]
        self.assertEqual(self.select(rules), ["WARN", "BLOCK"])

    def test_a_company_rule_neither_applies_nor_shadows_in_another_company(self):
        rules = [rule("ELSEWHERE", company=OTHER_COMPANY), group_rule("EVERYWHERE", GROUP)]
        self.assertEqual(self.select(rules, company=COMPANY), ["EVERYWHERE"])
        self.assertEqual(self.select(rules, company=OTHER_COMPANY), ["ELSEWHERE"])

    def test_a_group_named_like_the_customer_is_not_a_customer_rule(self):
        self.assertEqual(self.select([group_rule("GROUP", CUSTOMER_NAME)]), [])


class TestRuleOutcome(FrappeTestCase):
    def test_the_action_table(self):
        """The table in docs/overdue-limit/reference.md."""
        columns = [(SAVE, False), (SAVE, True), (SUBMIT, False), (SUBMIT, True)]
        table = {
            WARN_ON_SAVE: [WARN, WARN, None, None],
            BLOCK_ON_SAVE: [BLOCK, WARN, BLOCK, WARN],
            BLOCK_ON_SUBMIT: [WARN, WARN, BLOCK, WARN],
        }
        for action, row in table.items():
            for (stage, exempt), expected in zip(columns, row):
                with self.subTest(action=action, stage=stage, exempt=exempt):
                    self.assertEqual(rule_outcome(action, stage, exempt), expected)


class TestDecide(FrappeTestCase):
    def outcome_on(self, today, rules):
        return decide(rules, days_overdue(INVOICE.due_date, today), SALES_ROLES, SAVE).outcome

    def test_a_rule_starts_on_its_threshold_day(self):
        rules = [rule(action=BLOCK_ON_SAVE, threshold_days=20)]
        self.assertIsNone(self.outcome_on("2026-10-27", rules))
        self.assertEqual(self.outcome_on("2026-10-28", rules), BLOCK)

    def test_the_refusal_lists_only_the_rules_that_block_this_user(self):
        rules = [
            rule("WARN"),
            rule("EXEMPTED", action=BLOCK_ON_SAVE, exempt_roles=[EXEMPT_ROLE]),
            rule("BLOCK", action=BLOCK_ON_SAVE),
        ]
        verdict = decide(rules, 30, [EXEMPT_ROLE], SAVE)
        self.assertEqual((verdict.outcome, hit_names(verdict)), (BLOCK, ["BLOCK"]))

    def test_the_warning_lists_every_triggered_rule_and_no_other(self):
        rules = [
            rule("WARN", threshold_days=20),
            rule("NOTICE", action=BLOCK_ON_SUBMIT, threshold_days=25),
            rule("NOT YET", action=BLOCK_ON_SAVE, threshold_days=40),
        ]
        verdict = decide(rules, 30, SALES_ROLES, SAVE)
        self.assertEqual((verdict.outcome, hit_names(verdict)), (WARN, ["WARN", "NOTICE"]))


class TestMessage(FrappeTestCase):
    def render(self, action, user_roles):
        verdict = decide([rule(action=action, exempt_roles=[EXEMPT_ROLE])], 30, user_roles, SAVE)
        return message(verdict, CUSTOMER_NAME, INVOICE, 30)

    def test_a_blocked_user_is_told_which_roles_can_continue(self):
        self.assertIn(EXEMPT_ROLE, self.render(BLOCK_ON_SAVE, SALES_ROLES))

    def test_an_exempt_user_is_told_their_role_lets_them_continue(self):
        text = self.render(BLOCK_ON_SAVE, [EXEMPT_ROLE])
        self.assertIn("Your role lets you continue.", text)
        self.assertNotIn(EXEMPT_ROLE, text)

    def test_a_warn_rule_ignores_the_exempt_roles_the_form_hides(self):
        for user_roles in (SALES_ROLES, [EXEMPT_ROLE]):
            with self.subTest(user_roles=user_roles):
                text = self.render(WARN_ON_SAVE, user_roles)
                self.assertNotIn(EXEMPT_ROLE, text)
                self.assertNotIn("Your role lets you continue.", text)
