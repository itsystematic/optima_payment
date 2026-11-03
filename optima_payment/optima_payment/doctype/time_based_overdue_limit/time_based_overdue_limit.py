# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class TimeBasedOverdueLimit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from optima_payment.optima_payment.doctype.time_based_overdue_limit_exempt_role.time_based_overdue_limit_exempt_role import TimeBasedOverdueLimitExemptRole

		action: DF.Literal["Warn on Save", "Block on Save", "Block on Submit"]
		applies_to: DF.Literal["Customer", "Customer Group"]
		company: DF.Link | None
		enabled: DF.Check
		exempt_roles: DF.TableMultiSelect[TimeBasedOverdueLimitExemptRole]
		party: DF.DynamicLink
		threshold_days: DF.Int
	# end: auto-generated types

	def validate(self):
		self.validate_threshold_days()
		self.validate_unique_rule()

	def validate_threshold_days(self):
		if cint(self.threshold_days) <= 0:
			frappe.throw(_("Threshold Days must be greater than 0."))

	def validate_unique_rule(self):
		if not self.enabled:
			return

		duplicate = frappe.db.exists(
			self.doctype,
			{
				"name": ("!=", self.name),
				"enabled": 1,
				"applies_to": self.applies_to,
				"party": self.party,
				"company": self.company or ("is", "not set"),
				"action": self.action,
			},
		)
		if duplicate:
			frappe.throw(
				_("Enabled rule {0} already has the same Applies To, Party, Company and Action.").format(
					frappe.bold(duplicate)
				)
			)
