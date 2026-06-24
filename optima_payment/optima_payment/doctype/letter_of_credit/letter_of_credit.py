# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe import _
from frappe.model.document import Document


class LetterofCredit(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        account: DF.Link | None
        amended_from: DF.Link | None
        amount: DF.Currency
        bank: DF.Link
        bank_account: DF.Link | None
        bank_account_no: DF.Data | None
        bank_amount: DF.Float
        bank_facilities_account: DF.Link | None
        bank_rate_: DF.Percent
        banking_facilities: DF.Literal["Without Facilities", "With Facilities"]
        company: DF.Link | None
        conditions: DF.Literal["", "With Condition", "Without Condition"]
        cost_center: DF.Link
        customer: DF.Link | None
        end_date: DF.Date | None
        extend_validity: DF.Check
        facilities_rate_: DF.Percent
        facility_amount: DF.Float
        issue_commission: DF.Check
        issue_commission_amount: DF.Float
        lc_account: DF.Link | None
        lc_amount: DF.Currency
        lc_category: DF.Literal["Initial", "Final", "Advanced Payment", "Financial"]
        lc_number: DF.Data
        lc_percent: DF.Percent
        lc_status: DF.Literal["New", "Exists", "Issued", "Returned", "Expired", "Extended", "Lost"]
        lc_type: DF.Literal["Providing", "Receiving"]
        more_information: DF.TextEditor | None
        name_of_beneficiary: DF.Data
        net_amount: DF.Currency
        new_end_date: DF.Date | None
        no_of_extended_days: DF.Int
        posting_date: DF.Date
        project: DF.Link
        reference_docname: DF.DynamicLink
        reference_doctype: DF.Literal["Sales Order", "Purchase Order"]
        remarks: DF.SmallText | None
        returned_date: DF.Date | None
        start_date: DF.Date
        supplier: DF.Link | None
        tax_amount: DF.Currency
        validity: DF.Int
    # end: auto-generated types

    # ================================================================================================
    # DOCTYPE LIFECYCLE
    # ================================================================================================
    # Frappe's submittable-document hooks, in the order they actually fire:
    # validate -> before_submit -> on_submit -> on_cancel -> on_trash
    #
    # GL/Payment Entry integration is deferred to a later phase. For now, submit/cancel/
    # return/extend/loss only update status fields - no ledger entries are created here.

    def validate(self):
        self.validate_customer_or_supplier()
        self.validate_lc_number_and_beneficiary()
        self.validate_company_account()

    def before_submit(self):
        self.add_remarks()

    def on_submit(self):
        self.set_status()
        # TODO(phase 2): post GL via Payment Entry

    def on_cancel(self):
        pass

    def on_trash(self):
        pass

    # ================================================================================================
    # VALIDATION
    # ================================================================================================

    def validate_customer_or_supplier(self):
        if not (self.customer or self.supplier):
            frappe.throw(_("Select the customer or supplier."))

    def validate_lc_number_and_beneficiary(self):
        if not self.lc_number or not self.name_of_beneficiary:
            frappe.throw(_("Enter the Letter of Credit Number or name of the Beneficiary before submitting."))

    def validate_company_account(self):
        settings = self.get_optima_payment_setting()

        if not settings.lc_insurance_account:
            frappe.throw(_("Please set the Insurance Account under Optima Payment Setting."))

        if not settings.lc_receiving_insurance_account:
            frappe.throw(_("Please set the Receiving Insurance Account under Optima Payment Setting."))

        if not settings.lc_bank_fees_account:
            frappe.throw(_("Please set the Bank Fees Account under Optima Payment Setting."))

        if not settings.lc_loss_expense_account:
            frappe.throw(_("Please set the Loss Expense Account under Optima Payment Setting."))

    # ================================================================================================
    # SUBMIT / STATUS HELPERS
    # ================================================================================================

    def set_status(self):
        if self.lc_status == "New":
            if self.lc_type == "Providing":
                self.set("lc_status", "Issued")

            elif self.lc_type == "Receiving":
                self.set("lc_status", "Exists")

    def add_remarks(self):
        if not self.remarks:
            self.remarks = _("({}) project + ({}) Letter of Credit Number").format(self.project, self.lc_number)

    # ================================================================================================
    # WHITELISTED ACTIONS - Return / Extend / Loss custom buttons
    # ================================================================================================
    # GL postings/reversals are deferred to phase 2 (Payment Entry). These actions only
    # validate dates and update status fields for now.

    @frappe.whitelist()
    def lc_return(self, returned_date):
        recent_transaction_date = self.get_recent_transaction_date()

        returned_date = frappe.utils.getdate(returned_date)

        # ensure return date is after posting date
        if returned_date < recent_transaction_date:
            frappe.throw(_("Return date cannot be before posting date"))

        # TODO(phase 2): reverse GL entries via Payment Entry

        self.update_fields_dict({"lc_status": "Returned", "returned_date": returned_date})

        frappe.msgprint(_("Letter of Credit has been returned successfully"))

    @frappe.whitelist()
    def lc_extend_action(self, amount, end_date, days, extend_to_date, has_commission):
        last_transaction_date = self.get_recent_transaction_date()

        # ensure extend date is after posting date
        extend_to_date = frappe.utils.getdate(extend_to_date)
        if extend_to_date < last_transaction_date:
            frappe.throw(_("Extend date cannot be before posting date"))

        self.update_fields_dict(
            {
                "no_of_extended_days": self.no_of_extended_days + days,
                "lc_status": "Extended",
                "issue_commission_amount": self.issue_commission_amount + amount,
                "new_end_date": end_date,
                "extend_validity": 1,
            }
        )

        # TODO(phase 2): if has_commission, post commission GL via Payment Entry

        frappe.msgprint(_("Letter of Credit has been extended successfully"))

    @frappe.whitelist()
    def lc_loss_action(self, loss_date):
        # ensure loss date is after posting date
        recent_transaction_date = self.get_recent_transaction_date()

        loss_date = frappe.utils.getdate(loss_date)
        if loss_date < recent_transaction_date:
            frappe.throw(_("Loss date cannot be before posting date"))

        # TODO(phase 2): reverse original GL entries and post the loss pair via Payment Entry

        self.update_fields_dict({"lc_status": "Lost"})

        frappe.msgprint(_("Letter of Credit has been marked as lost successfully"))

    # ================================================================================================
    # SHARED HELPERS
    # ================================================================================================

    def get_company(self):
        from erpnext import get_default_company

        company = get_default_company()

        if self.company:
            company = self.company

        return frappe.get_doc("Company", company)

    def get_optima_payment_setting(self, company_name=None):
        """Return the per-company Optima Payment Setting document for this transaction."""

        company_name = company_name or self.get_company().name
        setting_name = frappe.db.get_value("Optima Payment Setting", {"company": company_name}, "name")

        if not setting_name:
            frappe.throw(
                _("Please create Optima Payment Setting for company {0}.").format(
                    frappe.bold(company_name)
                )
            )

        return frappe.get_cached_doc("Optima Payment Setting", setting_name)

    def get_recent_transaction_date(self):
        """Floor date for Return/Extend/Loss date validation.

        No GL history exists yet (GL/Payment Entry integration is phase 2), so this
        simply falls back to posting_date.
        """
        return frappe.utils.getdate(self.posting_date)

    def update_fields_dict(self, dict_updated):
        frappe.db.set_value("Letter of Credit", self.name, dict_updated, update_modified=True)
        self.reload()
