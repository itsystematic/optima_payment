# Copyright (c) 2026, IT Systematic and Contributors
# See license.txt

"""The rule's own validation: a positive threshold, and one enabled rule per party, company and
action."""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase

from optima_payment.overdue_limit.limit import BLOCK_ON_SAVE, WARN_ON_SAVE
from optima_payment.tests.utils import get_or_create_customer, make_overdue_limit

CUSTOMER = "Optima Overdue Test Customer"


class TestTimeBasedOverdueLimit(FrappeTestCase):
    def setUp(self):
        self.customer = get_or_create_customer(CUSTOMER)

    def tearDown(self):
        frappe.db.rollback()

    def test_the_threshold_must_be_above_zero(self):
        for days in (0, -5):
            with self.subTest(days=days), self.assertRaises(frappe.ValidationError):
                make_overdue_limit(party=self.customer, action=WARN_ON_SAVE, threshold_days=days)

    def test_a_second_enabled_rule_for_the_same_party_company_and_action_is_refused(self):
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE, threshold_days=20)
        with self.assertRaises(frappe.ValidationError):
            make_overdue_limit(party=self.customer, action=WARN_ON_SAVE, threshold_days=30)

    def test_rules_differing_in_action_company_or_enabled_are_not_duplicates(self):
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE)
        make_overdue_limit(party=self.customer, action=BLOCK_ON_SAVE)
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE, company=erpnext.get_default_company())
        make_overdue_limit(party=self.customer, action=WARN_ON_SAVE, enabled=0)

    def test_a_blank_company_is_not_filled_with_the_default_company(self):
        rule = make_overdue_limit(party=self.customer, action=WARN_ON_SAVE)
        self.assertFalse(frappe.db.get_value(rule.doctype, rule.name, "company"))

    def test_a_rule_can_be_saved_again(self):
        rule = make_overdue_limit(party=self.customer, action=WARN_ON_SAVE)
        rule.threshold_days = 25
        rule.save(ignore_permissions=True)
