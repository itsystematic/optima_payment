# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import copy

import frappe
import frappe.utils
from frappe import _
from frappe.types.DF import date
from frappe.utils import formatdate
from frappe.model.document import Document

from erpnext import get_default_company
from erpnext.accounts.utils import get_fiscal_years
from erpnext.utilities.regional import temporary_flag
from erpnext.accounts.general_ledger import make_entry, make_gl_entries
from erpnext.controllers.accounts_controller import update_gl_dict_with_regional_fields
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions


class BankGuaranteeBG(Document):
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
        bank_guarantee_account: DF.Link | None
        bank_guarantee_amount: DF.Currency
        bank_guarantee_number: DF.Data
        bank_guarantee_percent: DF.Percent
        bank_guarantee_purpose: DF.Literal["Bank Guarantee"]
        bank_guarantee_status: DF.Literal["New", "Exists", "Issued", "Returned", "Expired", "Extended", "Lost"]
        bank_rate_: DF.Percent
        banking_facilities: DF.Literal["Without Facilities", "With Facilities"]
        bg_type: DF.Literal["Providing", "Receiving"]
        company: DF.Link | None
        conditions: DF.Literal["", "With Condition", "Without Condition"]
        cost_center: DF.Link
        customer: DF.Link | None
        end_date: DF.Date | None
        extend_validity: DF.Check
        facilities_rate_: DF.Percent
        facility_amount: DF.Float
        guarantee_type: DF.Literal["Initial", "Final", "Advanced Payment", "Financial"]
        issue_commission: DF.Check
        issue_commission_amount: DF.Float
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

    def validate(self):
        self.validate_customer_or_supplier()
        self.validate_bank_or_cheque()
        self.validate_company_account()

    def before_submit(self):
        self.add_remarks()

    def on_submit(self):
        self.set_status()
        self.make_gl_entryies()

    def on_cancel(self):
        self.ignore_linked_doctypes = (
            "GL Entry",
            "Stock Ledger Entry",
            "Payment Ledger Entry",
            "Repost Payment Ledger",
            "Repost Payment Ledger Items",
            "Repost Accounting Ledger",
            "Repost Accounting Ledger Items",
            "Unreconcile Payment",
            "Unreconcile Payment Entries",
        )
        self.make_cancel_gl_entries()

    def on_trash(self):
        self.remove_gl_entries()
        self.remove_stock_ledger()
        self.remove_payment_ledger_entry()

    # ================================================================================================
    # VALIDATION
    # ================================================================================================

    def validate_customer_or_supplier(self):
        if not (self.customer or self.supplier):
            frappe.throw(_("Select the customer or supplier."))

    def validate_bank_or_cheque(self):
        if not self.bank_guarantee_number or not self.name_of_beneficiary:
            frappe.throw(_("Enter the Bank Guarantee Number or name of the Beneficiary before submitting."))

    def validate_company_account(self):
        settings = self.get_optima_payment_setting()

        if not settings.bank_guarantee_insurance_account:
            frappe.throw(_("Please set the Insurance Account under Optima Payment Setting."))

        if not settings.bank_guarantee_receiving_insurance_account:
            frappe.throw(_("Please set the Receiving Insurance Account under Optima Payment Setting."))

        if not settings.bank_guarantee_bank_fees_account:
            frappe.throw(_("Please set the Bank Fees Account under Optima Payment Setting."))

        if not settings.bank_guarantee_loss_expense_account:
            frappe.throw(_("Please set the Loss Expense Account under Optima Payment Setting."))

    # ================================================================================================
    # SUBMIT / STATUS HELPERS
    # ================================================================================================

    def set_status(self):
        if self.bank_guarantee_status == "New" :
            if self.bg_type == "Providing" :
                self.set("bank_guarantee_status" , "Issued")

            elif self.bg_type == "Receiving":
                self.set("bank_guarantee_status" , "Exists")

    def add_remarks(self):
        if not self.remarks:
            self.remarks = _("({}) project + ({}) Bank Guarantee Number").format(self.project, self.bank_guarantee_number)

    # ================================================================================================
    # WHITELISTED ACTIONS - Return / Extend / Loss custom buttons
    # ================================================================================================

    @frappe.whitelist()
    def bank_guarantee_return(self , returned_date) :
        recent_transaction_date = self.get_recent_transactoin_date()

        returned_date = frappe.utils.getdate(returned_date)

        # ensure extend date is after posting date
        if returned_date < recent_transaction_date :
            frappe.throw(_("Return date cannot be before posting date"))

        company = self.get_company()
        gl_entries = self.get_gl_entries()

        self.make_reverse_gl_entries(gl_entries, adv_adj=False, date=returned_date, company=company)

        self.update_fields_dict({"bank_guarantee_status" : "Returned" ,"returned_date" : returned_date })

    @frappe.whitelist()
    def make_extend_action(self ,amount ,end_date ,days ,extend_to_date, has_commission) :
        last_gl_entry_date = self.get_recent_transactoin_date()

        # ensure extend date is after posting date
        extend_to_date = frappe.utils.getdate(extend_to_date)
        if extend_to_date < last_gl_entry_date :
            frappe.throw(_("Extend date cannot be before posting date"))

        self.update_fields_dict(
            {
                "no_of_extended_days": self.no_of_extended_days + days,
                "bank_guarantee_status" : "Extended" ,
                "issue_commission_amount" : self.issue_commission_amount + amount,
                "new_end_date" : end_date ,
                "extend_validity" : 1
            }
        )

        # no commission? then no need to make gl entry
        if has_commission:
            self.make_gl_entry_of_extend(extend_to_date, amount)

    @frappe.whitelist()
    def make_loss_action(self , loss_date) :
        """
            reverse existing gls, and make new gls
        """
        # ensure loss date is after posting date
        recent_transaction_date = self.get_recent_transactoin_date()

        loss_date = frappe.utils.getdate(loss_date)
        if loss_date < recent_transaction_date : # After
            frappe.throw(_("Loss date cannot be before posting date"))

        settings = self.get_optima_payment_setting()
        gl_entries = self.get_gl_entries()

        self.make_reverse_gl_entries(gl_entries, adv_adj=False, date=loss_date, company=self.get_company())

        gl_entries = []

        if self.bg_type == "Providing":
            self.make_row_in_gl(
                account= settings.bank_guarantee_loss_expense_account ,
                credit_or_debit="debit" ,
                amount= self.bank_guarantee_amount,
                cost_center = self.cost_center,
                posting_date = loss_date ,
                gl_entries= gl_entries,
            )
            self.make_row_in_gl(
                account=self.account ,
                credit_or_debit="credit" ,
                amount= self.bank_guarantee_amount ,
                posting_date = loss_date ,
                cost_center= self.cost_center,
                gl_entries= gl_entries,
            )

        elif self.bg_type == "Receiving":
            self.make_row_in_gl(
                account=self.account ,
                credit_or_debit="debit" ,
                amount= self.bank_guarantee_amount ,
                posting_date = loss_date ,
                cost_center= self.cost_center,
                gl_entries= gl_entries,
            )
            self.make_row_in_gl(
                account= settings.bank_guarantee_receiving_insurance_account ,
                credit_or_debit="credit" ,
                amount= self.bank_guarantee_amount,
                posting_date = loss_date ,
                cost_center = self.cost_center,
                gl_entries= gl_entries,
            )

        make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")
        self.update_fields_dict({ "bank_guarantee_status" : "Lost" })

    # ================================================================================================
    # GL ENTRY CONSTRUCTION
    # ================================================================================================

    def make_gl_entryies(self):

        gl_entries = self.get_gl_entries()
        make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")

    def make_cancel_gl_entries(self):

        d = frappe.get_all("GL Entry", filters={'voucher_no': self.name},
                            fields=['company', 'fiscal_year', 'voucher_type',
                                    'credit', 'debit_in_account_currency',
                                    'voucher_no', 'remarks', 'against', 'debit',
                                    'credit_in_account_currency', 'is_opening',
                                    'party_type', 'party', 'project', 'voucher_detail_no',
                                    'account', 'cost_center', 'posting_date', 'is_bank_guarantee_comission_entry'
                                    ]
            )
        make_gl_entries(d, cancel=True, merge_entries=False ,update_outstanding="No")

    def get_gl_entries(self) -> list[dict]:
        gl_entries = []
        company = self.get_company()
        settings = self.get_optima_payment_setting(company.name)
        type_debit , type_credit = self.get_debit_or_credit()

        posting_date = self.get_posting_date()

        self.make_gl_of_providing(gl_entries , type_debit , type_credit , company, settings, posting_date)

        return gl_entries

    def make_gl_of_providing(self ,gl_entries , type_debit , type_credit , company, settings, posting_date):
        if self.bg_type == "Providing" :


            self.make_row_in_gl(
                account= self.bank_guarantee_account if self.bank_guarantee_account  else  settings.bank_guarantee_insurance_account ,
                credit_or_debit=type_debit ,
                amount= self.bank_amount ,
                cost_center = self.cost_center ,
                gl_entries=gl_entries,
                posting_date = posting_date,
            )

            self.make_row_in_gl(
                posting_date=posting_date,
                account=self.account,
                credit_or_debit=type_credit,
                amount= self.bank_amount,
                gl_entries= gl_entries,
                )

            if self.bank_guarantee_status != "Returned" and self.issue_commission :
                self.make_row_in_gl(
                    account=settings.bank_guarantee_bank_fees_account ,
                    credit_or_debit=type_debit ,
                    amount= self.issue_commission_amount,
                    cost_center = self.cost_center,
                    gl_entries= gl_entries,
                    posting_date = posting_date,
                    is_bank_guarantee_comission_entry = True
                )
                self.make_row_in_gl(
                    account=self.account ,
                    credit_or_debit=type_credit ,
                    amount= self.issue_commission_amount ,
                    gl_entries= gl_entries,
                    posting_date = posting_date,
                    is_bank_guarantee_comission_entry = True
                )

    def make_gl_entry_of_extend(self, extend_to_date, amount) :
        gl_entries = []
        if self.bg_type == "Providing" :
            company = self.get_company()
            settings = self.get_optima_payment_setting(company.name)
            self.make_row_in_gl(
                account=settings.bank_guarantee_bank_fees_account ,
                credit_or_debit="debit" ,
                amount= amount ,
                cost_center = self.cost_center,
                gl_entries= gl_entries,
                posting_date = extend_to_date,
            )
            self.make_row_in_gl(
                account= self.account if self.account else company.default_bank_account ,
                credit_or_debit="credit" ,
                amount= amount ,
                cost_center= self.cost_center,
                gl_entries= gl_entries,
                posting_date = extend_to_date,
            )
            make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")

    def make_reverse_gl_entries(self,gl_entries=None, adv_adj=False, date=None, company=None):
        """
        Get original gl entries of the voucher
        and make reverse gl entries by swapping debit and credit
        """

        gl_entries = gl_entries or []
        if gl_entries:
            for entry in gl_entries:
                if entry.get("is_bank_guarantee_comission_entry") == True: # bank commiosion do net return, skip it's gls, to aviod reversing
                    continue
                new_gle = copy.deepcopy(entry)
                new_gle["name"] = None
                debit = new_gle.get("debit", 0)
                credit = new_gle.get("credit", 0)

                debit_in_account_currency = new_gle.get("debit_in_account_currency", 0)
                credit_in_account_currency = new_gle.get("credit_in_account_currency", 0)

                new_gle["debit"] = credit
                new_gle["credit"] = debit
                new_gle["debit_in_account_currency"] = credit_in_account_currency
                new_gle["credit_in_account_currency"] = debit_in_account_currency

                if date: # for loss  action, create the reverse gl entry with loss date
                    new_gle["posting_date"] = date

                if new_gle["debit"] or new_gle["credit"]:
                    make_entry(new_gle, adv_adj, "Yes")

    def make_row_in_gl(
        self,
        account,
        credit_or_debit,
        amount,
        gl_entries:list =[] ,
        posting_date=None,
        is_bank_guarantee_comission_entry = False ,
        *args , **kwargs
    ) :
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": account ,
                    credit_or_debit: amount,
                    credit_or_debit + "_in_account_currency": amount ,
                    "project": self.project ,
                    "posting_date" : posting_date,
                    "is_bank_guarantee_comission_entry" : is_bank_guarantee_comission_entry
                },
        ))

    def get_gl_dict(self, args, account_currency=None, item=None):

        """this method populates the common properties of a gl entry record"""

        posting_date = args.get("posting_date")

        fiscal_years = get_fiscal_years(posting_date, company=self.company)
        if len(fiscal_years) > 1:
            frappe.throw(
                _("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
                    formatdate(posting_date)
                )
            )
        else:
            fiscal_year = fiscal_years[0][0]

        gl_dict = frappe._dict(
            {
                "company": self.company,
                "fiscal_year": fiscal_year,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "remarks": self.get("remarks") or self.get("remark"),
                "against": self.get("customer") or self.get("supplier"),
                "debit": 0,
                "credit": 0,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": 0,
                "is_opening": self.get("is_opening") or "No",
                "party_type": None,
                "party": None,
                "cost_center": self.get("cost_center"),
                "project": self.get("project"),
                "post_net_value": args.get("post_net_value"),
                "voucher_detail_no": args.get("voucher_detail_no"),
            }
        )

        with temporary_flag("company", self.company):
            update_gl_dict_with_regional_fields(self, gl_dict)

        accounting_dimensions = get_accounting_dimensions()
        dimension_dict = frappe._dict()

        for dimension in accounting_dimensions:
            dimension_dict[dimension] = self.get(dimension)
            if item and item.get(dimension):
                dimension_dict[dimension] = item.get(dimension)

        gl_dict.update(dimension_dict)
        gl_dict.update(args)

        if not gl_dict.account :

            frappe.throw(_("Account is mandatory"))

        return gl_dict

    def get_debit_or_credit(self):
        type_debit , type_credit = "debit" , "credit"
        if self.bank_guarantee_status in ["Returned"] :
            type_debit , type_credit = "credit" , "debit"

        return type_debit , type_credit

    # ================================================================================================
    # CLEANUP ON DELETE
    # ================================================================================================

    def remove_gl_entries(self) :

        frappe.db.sql(
                "delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s",
                (self.doctype, self.name)
        )

    def remove_stock_ledger(self) :
        frappe.db.sql(
            "delete from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s",
            (self.doctype, self.name),
        )

    def remove_payment_ledger_entry(self) :
        ple = frappe.qb.DocType("Payment Ledger Entry")
        frappe.qb.from_(ple).delete().where(
            (ple.voucher_type == self.doctype) & (ple.voucher_no == self.name)
        ).run()

    # ================================================================================================
    # SHARED HELPERS
    # ================================================================================================

    def get_company(self) :
        company = get_default_company()

        if self.company  :
            company = self.company

        return frappe.get_doc("Company" , company)

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

    def get_recent_transactoin_date(self) -> date:
        """
            get recent transaction date for the voucher
            To Ensure that next transation is after previous one

            Falls back to posting_date when no GL Entry exists yet (e.g. a Receiving
            guarantee that hasn't posted any GL on submit) so callers always get a
            valid floor to compare against.
        """
        voucher_no = self.name
        d = frappe.get_all("GL Entry", filters={'voucher_no': voucher_no}, pluck='posting_date',order_by='posting_date desc', limit=1)

        recent_transaction_date = d[0] if d else self.posting_date

        return frappe.utils.getdate(recent_transaction_date)

    def get_posting_date(self):
        if self.bank_guarantee_status == "Returned":
            posting_date = self.get("returned_date") or self.get("posting_date")

        elif self.bank_guarantee_status == "Extended":
            posting_date = self.get("end_date")

        elif self.bank_guarantee_status == "Lost":
            posting_date = self.get("end_date")

        else :
            posting_date = self.get("posting_date") or self.get("posting_date")

        return posting_date

    def update_fields_dict(self, dict_updated):
        frappe.db.set_value("Bank Guarantee-BG", self.name , dict_updated , update_modified=True)
        frappe.db.commit()
        self.reload()
