# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
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
        bank_amount: DF.Currency
        bank_facilities_account: DF.Link | None
        bank_rate_: DF.Percent
        banking_facilities: DF.Literal["Without Facilities", "With Facilities"]
        company: DF.Link | None
        conditions: DF.Literal["", "With Condition", "Without Condition"]
        cost_center: DF.Link
        customer: DF.Link | None
        end_date: DF.Date | None
        extend_validity: DF.Check
        extended_cash_margin_amount: DF.Currency
        extended_facility_amount: DF.Currency
        facilities_rate_: DF.Percent
        facility_amount: DF.Currency
        issue_commission: DF.Check
        issue_commission_amount: DF.Float
        lc_account: DF.Link | None
        lc_amount: DF.Currency
        lc_category: DF.Literal["Sight", "Deferred"]
        lc_number: DF.Data
        lc_percent: DF.Percent
        lc_status: DF.Literal["New", "Exists", "Issued", "Returned", "Expired", "Extended", "Closed"]
        pre_close_status: DF.Data | None
        reopen_date: DF.Date | None
        lc_type: DF.Literal["Providing", "Receiving"]
        mode_of_payment: DF.Link
        more_information: DF.TextEditor | None
        name_of_beneficiary: DF.Data
        net_amount: DF.Currency
        new_end_date: DF.Date | None
        no_of_extended_days: DF.Int
        number_of_deferred_days: DF.Int
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
    def validate(self):
        self.validate_customer_or_supplier()
        self.validate_lc_number_and_beneficiary()
        self.validate_company_account()
        self.validate_mode_of_payment()

    def before_submit(self):
        self.add_remarks()

    def on_submit(self):
        self.set_status()
        self.make_payment_entries()

    def on_cancel(self):
        self.ignore_linked_doctypes = (
            "Payment Entry",
            "GL Entry",
            "Payment Ledger Entry",
            "Repost Payment Ledger",
            "Repost Payment Ledger Items",
            "Repost Accounting Ledger",
            "Repost Accounting Ledger Items",
            "Unreconcile Payment",
            "Unreconcile Payment Entries",
        )
        self.cancel_linked_payment_entries()

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


    def validate_mode_of_payment(self):
        
        if not self.mode_of_payment:
            frappe.throw(_("Mode of Payment must be set."))

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
    # PAYMENT ENTRY CONSTRUCTION
    # ================================================================================================
    # GL impact is posted via Payment Entry (Internal Transfer) documents instead of
    # raw GL Entry rows - submitting/cancelling the Payment Entry handles GL
    # posting/reversal automatically through its own controller.
    #
    # Commission rule: commissions are a permanent bank cost — they are NEVER reversed,
    # regardless of what happens to the LC (Return, Cancel, etc.).  Collateral transfers
    # (the main submit PE and any extend amount PEs) ARE reversed on Return.

    def make_payment_entries(self):
        paid_to, paid_from = self.get_payment_entry_accounts()

        commission_amount = None
        if self.lc_type == "Providing" and self.issue_commission:
            commission_amount = self.issue_commission_amount

        self.make_payment_entry(
            paid_to,
            paid_from,
            self.bank_amount,
            posting_date=self.posting_date,
            commission_amount=commission_amount,
        )

    def get_payment_entry_accounts(self):
        """Return (paid_to, paid_from) for the initial submit-time posting."""
        settings = self.get_optima_payment_setting()

        if self.lc_type == "Providing":
            paid_to = self.lc_account or settings.lc_insurance_account
            paid_from = self.account
        else:
            paid_to = self.account
            paid_from = self.lc_account or settings.lc_receiving_insurance_account

        return paid_to, paid_from

    def make_return_payment_entry(self, returned_date):
        # Reverse every collateral PE (submit + extend amount PEs) by swapping
        # paid_from/paid_to on each.  Commission PEs are excluded — commissions
        # are a permanent bank cost that survive a Return.
        collateral_entries = frappe.get_all(
            "Payment Entry",
            filters={
                "letter_of_credit": self.name,
                "docstatus": 1,
                "is_lc_commission_entry": 0,
                "is_lc_loss_entry": 0,
                "is_lc_return_entry": 0,
                "is_system_generated": 1,
            },
            fields=["paid_from", "paid_to", "paid_amount"],
        )
        for pe in collateral_entries:
            self.make_payment_entry(
                pe.paid_from,
                pe.paid_to,
                pe.paid_amount,
                posting_date=returned_date,
                is_lc_return_entry=True,
            )

    def make_extend_commission_payment_entry(self, extend_to_date, amount):
        if self.lc_type != "Providing":
            return

        settings = self.get_optima_payment_setting()
        company = self.get_company()

        self.make_payment_entry(
            settings.lc_bank_fees_account,
            self.account or company.default_bank_account,
            amount,
            posting_date=extend_to_date,
            is_lc_commission_entry=True,
        )

    def make_close_payment_entry(self, close_date, close_amount):
        # Reversed direction — same account swap logic as Return.
        paid_to, paid_from = self.get_payment_entry_accounts()
        self.make_payment_entry(
            paid_from,
            paid_to,
            flt(close_amount),
            posting_date=close_date,
            is_lc_close_entry=True,
        )

    def make_payment_entry(
        self,
        paid_to,
        paid_from,
        amount,
        posting_date=None,
        is_lc_commission_entry=False,
        is_lc_loss_entry=False,
        is_lc_return_entry=False,
        is_lc_close_entry=False,
        commission_amount=None,
    ):

        pe = frappe.new_doc("Payment Entry")
        pe.update(
            {
                "payment_type": "Internal Transfer",
                "company": self.company,
                "posting_date": posting_date or self.posting_date,
                "mode_of_payment": self.mode_of_payment,
                "paid_from": paid_from,
                "paid_to": paid_to,
                "paid_amount": amount,
                "received_amount": amount,
                "project": self.project,
                "reference_no": self.lc_number,
                "reference_date": posting_date or self.posting_date,
                "letter_of_credit": self.name,
                "is_lc_commission_entry": is_lc_commission_entry,
                "is_lc_loss_entry": is_lc_loss_entry,
                "is_lc_return_entry": is_lc_return_entry,
                "is_lc_close_entry": is_lc_close_entry,
                "is_system_generated": 1,
            }
        )

        if commission_amount:
            settings = self.get_optima_payment_setting()
            pe.append(
                "taxes",
                {
                    "charge_type": "Actual",
                    "account_head": settings.lc_bank_fees_account,
                    "add_deduct_tax": "Add",
                    "tax_amount": commission_amount,
                    "description": _("Letter of Credit Issue Commission"),
                    "cost_center": self.cost_center,
                },
            )

        pe.insert(ignore_permissions=True)
        pe.submit()
        return pe

    def cancel_linked_payment_entries(self, skip_commission=False):
        payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"letter_of_credit": self.name, "docstatus": 1},
            fields=["name", "is_lc_commission_entry", "is_lc_loss_entry", "is_lc_return_entry", "is_lc_close_entry", "is_system_generated"],
            order_by="creation desc",
        )

        for pe in payment_entries:
            if skip_commission and pe.is_lc_commission_entry:
                continue

            frappe.get_doc("Payment Entry", pe.name).cancel()

    # ================================================================================================
    # WHITELISTED ACTIONS - Return / Extend / Loss custom buttons
    # ================================================================================================

    @frappe.whitelist()
    def lc_return(self, returned_date):
        recent_transaction_date = self.get_recent_transaction_date()

        returned_date = getdate(returned_date)

        # ensure return date is after posting date
        if returned_date < recent_transaction_date:
            frappe.throw(_("Return date cannot be before posting date"))

        self.make_return_payment_entry(returned_date)

        self.update_fields_dict({"lc_status": "Returned", "returned_date": returned_date})

        frappe.msgprint(_("Letter of Credit has been returned successfully"), indicator="green", alert=True)

    @frappe.whitelist()
    def lc_extend_action(
        self, commission_amount, end_date, extended_days, extend_to_date, has_commission,
        has_amount_extension=False, lc_amount_extension=0,
        new_cash_margin_amount=0, new_facilities_amount=0,
    ):
        last_transaction_date = self.get_recent_transaction_date()

        # ensure extend date is after posting date
        extend_to_date = getdate(extend_to_date)
        if extend_to_date < last_transaction_date:
            frappe.throw(_("Extend date cannot be before posting date"))

        self.update_fields_dict(
            {
                "no_of_extended_days": self.no_of_extended_days + extended_days,
                "lc_status": "Extended",
                "issue_commission_amount": self.issue_commission_amount + commission_amount,
                "new_end_date": end_date,
                "extend_validity": 1,
                "extended_cash_margin_amount": self.extended_cash_margin_amount + flt(new_cash_margin_amount),
                "extended_facility_amount": self.extended_facility_amount + flt(new_facilities_amount),
            }
        )

        if has_amount_extension and flt(lc_amount_extension):
            # Collateral PE for the extended amount.  Commission is folded in as a
            # taxes row so both post in one document — same pattern as submit.
            paid_to, paid_from = self.get_payment_entry_accounts()
            self.make_payment_entry(
                paid_to,
                paid_from,
                flt(lc_amount_extension),
                posting_date=extend_to_date,
                commission_amount=flt(commission_amount) if has_commission else None,
            )
        elif has_commission:
            # Validity-only extension — no collateral PE to host the commission,
            # so it gets its own standalone PE (permanent cost, never reversed).
            self.make_extend_commission_payment_entry(extend_to_date, commission_amount)

        frappe.msgprint(_("Letter of Credit has been extended successfully"), indicator="green", alert=True)

    @frappe.whitelist()
    def lc_close_action(self, close_date, close_amount):
        recent_transaction_date = self.get_recent_transaction_date()

        close_date = getdate(close_date)
        if close_date < recent_transaction_date:
            frappe.throw(_("Close date cannot be before the last transaction date"))

        self.make_close_payment_entry(close_date, close_amount)

        self.update_fields_dict({"pre_close_status": self.lc_status, "lc_status": "Closed"})

        frappe.msgprint(_("Letter of Credit has been closed successfully"), indicator="green", alert=True)

    @frappe.whitelist()
    def lc_reopen_action(self, reopen_date):
        if self.lc_status != "Closed":
            frappe.throw(_("Letter of Credit is not in Closed status"))

        if not self.pre_close_status:
            frappe.throw(_("Cannot determine previous status — pre_close_status is missing"))

        self.update_fields_dict({
            "lc_status": self.pre_close_status,
            "pre_close_status": None,
            "reopen_date": reopen_date,
        })

        frappe.msgprint(_("Letter of Credit has been re-opened successfully"), indicator="green", alert=True)

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

        Sourced from the most recent linked Payment Entry, falling back to
        posting_date when none exists yet (e.g. before the LC has been submitted).
        """
        dates = frappe.get_all(
            "Payment Entry",
            filters={"letter_of_credit": self.name, "docstatus": 1},
            pluck="posting_date",
            order_by="posting_date desc",
            limit=1,
        )

        recent_transaction_date = dates[0] if dates else self.posting_date

        return getdate(recent_transaction_date)

    def update_fields_dict(self, dict_updated):
        frappe.db.set_value("Letter of Credit", self.name, dict_updated, update_modified=True)
        self.reload()
