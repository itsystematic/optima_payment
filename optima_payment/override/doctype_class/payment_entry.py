from erpnext.accounts.doctype.payment_entry.payment_entry import (
    get_account_details,
)
import frappe
from frappe import _
import erpnext
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import (
    make_gl_entries,
    process_gl_map,
)
from optima_payment import active_for_company
from erpnext.accounts.utils import cancel_exchange_gain_loss_journal

# def get_custom_class() -> type:
#     """
#     Returns the custom class name based on installed apps

#     Returns:
#         type: The custom class name
#     """
#     if "hrms" in frappe.get_installed_apps():
#         from hrms.overrides.employee_payment_entry import EmployeePaymentEntry
#         return EmployeePaymentEntry
#     else :
#         from erpnext.accounts.doctype.payment_entry.payment_entry import  PaymentEntry
#         return PaymentEntry
if "hrms" in frappe.get_installed_apps():
    from hrms.overrides.employee_payment_entry import EmployeePaymentEntry

    PAYMENTENTRY = EmployeePaymentEntry
else:
    from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

    PAYMENTENTRY = PaymentEntry


class CustomPaymentEntry(PAYMENTENTRY):
    def validate(self):
        super().validate()
        self.validate_company_expenses()

    def on_submit(self):
        if self.difference_amount and self.get("multi_expense") == 0:
            frappe.throw(_("Difference Amount must be zero"))
        self.make_gl_entries()

        self.update_outstanding_amounts()
        self.update_advance_paid()
        self.update_payment_schedule()
        self.set_status()

    # def build_gl_map(self):
    #     if self.payment_type in ("Receive", "Pay") and not self.get("party_account_field"):
    #         self.setup_party_account_field()

    #     gl_entries = []
    #     self.add_party_gl_entries(gl_entries)
    #     self.add_bank_gl_entries(gl_entries)
    #     self.add_deductions_gl_entries(gl_entries)
    #     self.add_tax_gl_entries(gl_entries)
    #     add_regional_gl_entries(gl_entries, self)

    #     return gl_entries

    # @active_for_company
    def add_party_gl_entries(self, gl_entries):
        if not self.party_account:
            return
        # if self.is_endorsed_cheque :
        #     return
        if self.payment_type == "Receive":
            against_account = self.paid_to
        else:
            against_account = self.paid_from

        party_account_type = frappe.db.get_value(
            "Party Type", self.party_type, "account_type"
        )

        party_gl_dict = self.get_gl_dict(
            {
                "account": self.party_account,
                "party_type": self.party_type,
                "party": self.party,
                "against": against_account,
                "account_currency": self.party_account_currency,
                "cost_center": self.cost_center,
            },
            item=self,
        )

        for d in self.get("references"):
            # re-defining dr_or_cr for every reference in order to avoid the last value affecting calculation of reverse
            dr_or_cr = "credit" if self.payment_type == "Receive" else "debit"
            cost_center = self.cost_center
            if d.reference_doctype == "Sales Invoice" and not cost_center:
                cost_center = frappe.db.get_value(
                    d.reference_doctype, d.reference_name, "cost_center"
                )

            gle = party_gl_dict.copy()

            allocated_amount_in_company_currency = (
                self.calculate_base_allocated_amount_for_reference(d)
            )

            if (
                d.reference_doctype in ["Sales Invoice", "Purchase Invoice"]
                and d.allocated_amount < 0
                and (
                    (party_account_type == "Receivable" and self.payment_type == "Pay")
                    or (
                        party_account_type == "Payable"
                        and self.payment_type == "Receive"
                    )
                )
            ):
                # reversing dr_cr because because it will get reversed in gl processing due to negative amount
                dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

            gle.update(
                {
                    dr_or_cr: allocated_amount_in_company_currency,
                    dr_or_cr + "_in_account_currency": d.allocated_amount,
                    "against_voucher_type": d.reference_doctype,
                    "against_voucher": d.reference_name,
                    "cost_center": cost_center,
                }
            )
            gl_entries.append(gle)

        if self.unallocated_amount:
            dr_or_cr = "credit" if self.payment_type == "Receive" else "debit"
            exchange_rate = self.get_exchange_rate()
            base_unallocated_amount = self.unallocated_amount * exchange_rate

            gle = party_gl_dict.copy()
            gle.update(
                {
                    dr_or_cr + "_in_account_currency": self.unallocated_amount,
                    dr_or_cr: base_unallocated_amount,
                }
            )

            if self.book_advance_payments_in_separate_party_account:
                gle.update(
                    {
                        "against_voucher_type": "Payment Entry",
                        "against_voucher": self.name,
                    }
                )
            gl_entries.append(gle)

    def add_bank_gl_entries(self, gl_entries):
        if self.payment_type in ("Pay", "Internal Transfer"):
            self._add_pay_gl_entry(gl_entries)

        if self.payment_type in ("Receive", "Internal Transfer"):
            self._add_receive_gl_entry(gl_entries)

    def _add_pay_gl_entry(self, gl_entries):
        gl_entry = {
            "account": self.paid_from,
            "account_currency": self.paid_from_account_currency,
            "against": self.party if self.payment_type == "Pay" else self.paid_to,
            "credit_in_account_currency": self.paid_amount,
            "credit": self.base_paid_amount,
            "cost_center": self.cost_center,
            "post_net_value": True,
        }

        if self.is_endorsed_cheque:
            gl_entry.update(
                {
                    "against_voucher": self.receivable_cheque,
                    "against_voucher_type": self.doctype,
                }
            )

        gl_entries.append(self.get_gl_dict(gl_entry, item=self))

    def _add_receive_gl_entry(self, gl_entries):
        gl_entry = {
            "account": self.paid_to,
            "account_currency": self.paid_to_account_currency,
            "against": self.party if self.payment_type == "Receive" else self.paid_from,
            "debit_in_account_currency": self.received_amount,
            "debit": self.base_received_amount,
            "cost_center": self.cost_center,
        }

        gl_entries.append(self.get_gl_dict(gl_entry, item=self))

    # --------------------------------- Multi Expense Logic ---------------------------------
    def validate_company_expenses(self):
        if self.get("multi_expense") == 1:
            self.flags.ignore_mandatory = True

    def set_missing_values(self):
        if self.payment_type == "Internal Transfer":
            for field in (
                "party",
                "party_balance",
                "total_allocated_amount",
                "base_total_allocated_amount",
                "unallocated_amount",
            ):
                self.set(field, None)
            self.references = []
        else:
            if self.get("multi_expense") == 0:
                if not self.party_type:
                    frappe.throw(_("Party Type is mandatory"))

                if not self.party and self.get("multi_expense") == 0:
                    frappe.throw(_("Party is mandatory"))

                _party_name = (
                    "title"
                    if self.party_type == "Shareholder"
                    else self.party_type.lower() + "_name"
                )

                if frappe.db.has_column(self.party_type, _party_name):
                    self.party_name = frappe.db.get_value(
                        self.party_type, self.party, _party_name
                    )
                else:
                    self.party_name = frappe.db.get_value(
                        self.party_type, self.party, "name"
                    )

        if self.party:
            if not self.party_balance:
                self.party_balance = get_balance_on(
                    party_type=self.party_type,
                    party=self.party,
                    date=self.posting_date,
                    company=self.company,
                )

            if not self.party_account:
                party_account = get_party_account(
                    self.party_type, self.party, self.company
                )
                self.set(self.party_account_field, party_account)
                self.party_account = party_account

        if self.paid_from and not (
            self.paid_from_account_currency or self.paid_from_account_balance
        ):
            acc = get_account_details(
                self.paid_from, self.posting_date, self.cost_center
            )
            self.paid_from_account_currency = acc.account_currency
            self.paid_from_account_balance = acc.account_balance

        if self.paid_to and not (
            self.paid_to_account_currency or self.paid_to_account_balance
        ):
            acc = get_account_details(self.paid_to, self.posting_date, self.cost_center)
            self.paid_to_account_currency = acc.account_currency
            self.paid_to_account_balance = acc.account_balance

        self.party_account_currency = (
            self.paid_from_account_currency
            if self.payment_type == "Receive"
            else self.paid_to_account_currency
        )

    def validate_mandatory(self):
        if self.get("multi_expense") == 0:
            super().validate_mandatory()

    def build_gl_map(self):
        if self.payment_type in ("Receive", "Pay") and not self.get(
            "party_account_field"
        ):
            self.setup_party_account_field()

        gl_entries = []
        if not self.get("multi_expense"):
            self.add_party_gl_entries(gl_entries)
        self.make_company_expense(gl_entries)
        self.add_bank_gl_entries(gl_entries)
        self.add_deductions_gl_entries(gl_entries)
        self.add_tax_gl_entries(gl_entries)
        return gl_entries

    def make_company_expense(self, gl_entries):
        if self.get("company_expense") and self.multi_expense == 1:
            for account in self.company_expense:
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": account.default_account,
                            "account_currency": self.paid_from_account_currency,
                            "debit_in_account_currency": account.amount,
                            "party": account.party or None,
                            "party_type": account.party_type or None,
                            "debit": account.amount,
                            "cost_center": account.cost_center or None,
                            "remarks": account.remarks or None,
                        },
                        item=self,
                    )
                )

    def make_gl_entries(self, cancel=0, adv_adj=0):
        gl_entries = self.build_gl_map()
        gl_entries = process_gl_map(gl_entries, merge_entries=False)
        make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
        if cancel:
            cancel_exchange_gain_loss_journal(
                frappe._dict(doctype=self.doctype, name=self.name)
            )
        else:
            self.make_exchange_gain_loss_journal()

        self.make_advance_gl_entries(cancel=cancel)


@erpnext.allow_regional
def add_regional_gl_entries(gl_entries, doc):

    return
