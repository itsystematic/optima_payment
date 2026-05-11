from erpnext.accounts.doctype.payment_entry.payment_entry import (
    PaymentEntry,
    get_account_details,
    get_reference_details,
)
import frappe
from frappe import _
import erpnext
from erpnext.accounts.general_ledger import (
    make_gl_entries,
    process_gl_map,
)
from optima_payment import active_for_company
from erpnext.accounts.utils import cancel_exchange_gain_loss_journal
from erpnext import get_company_currency
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import cint, flt

# Check if optima_hr is installed
HAS_OPTIMA_HR = "optima_hr" in frappe.get_installed_apps()
HRMS_EMPLOYEE_REFERENCE_DOCTYPES = (
    "Expense Claim",
    "Employee Advance",
    "Gratuity",
    "Leave Encashment",
)
OPTIMA_EMPLOYEE_REFERENCE_DOCTYPES = ("Leave Dues", "End of Service Benefits")

if "hrms" in frappe.get_installed_apps():
    try:
        from hrms.overrides.employee_payment_entry import (
            EmployeePaymentEntry,
            get_reference_details_for_employee,
        )

        HAS_HRMS = True
        BasePaymentEntry = EmployeePaymentEntry
    except ImportError:
        HAS_HRMS = False
        BasePaymentEntry = PaymentEntry
else:
    HAS_HRMS = False
    BasePaymentEntry = PaymentEntry


class CustomPaymentEntry(BasePaymentEntry):
    """Payment Entry override with Optima HR and multi-expense support."""

    # ================================================================================================
    # OPTIMA HR INTEGRATION - Reference Doctypes Support
    # ================================================================================================
    # These methods add support for Optima HR custom doctypes (Leave Dues, End of Service Benefits)
    # in Payment Entry references
    
    def get_valid_reference_doctypes(self):
        """Extend the upstream employee reference doctypes with Optima HR doctypes."""
        doctypes = tuple(super().get_valid_reference_doctypes() or ())

        if self.party_type != "Employee" or not HAS_OPTIMA_HR:
            return doctypes

        # Preserve upstream ordering while avoiding duplicate doctypes.
        return tuple(dict.fromkeys(doctypes + OPTIMA_EMPLOYEE_REFERENCE_DOCTYPES))
    
    def set_missing_ref_details(
        self,
        force: bool = False,
        update_ref_details_only_for: list | None = None,
        reference_exchange_details: dict | None = None,
    ) -> None:
        """Override to support optima_hr reference doctypes"""
        for d in self.get("references"):
            if d.allocated_amount:
                if update_ref_details_only_for and (
                    (d.reference_doctype, d.reference_name) not in update_ref_details_only_for
                ):
                    continue

                ref_details = get_payment_reference_details(
                    d.reference_doctype,
                    d.reference_name,
                    self.party_account_currency,
                    self.party_type,
                    self.party,
                )

                # Only update exchange rate when the reference is Journal Entry
                if (
                    reference_exchange_details
                    and d.reference_doctype == reference_exchange_details.reference_doctype
                    and d.reference_name == reference_exchange_details.reference_name
                ):
                    ref_details.update({"exchange_rate": reference_exchange_details.exchange_rate})

                for field, value in ref_details.items():
                    if d.exchange_gain_loss:
                        continue

                    if field == "exchange_rate" or not d.get(field) or force:
                        if self.get("_action") in ("submit", "cancel"):
                            d.db_set(field, value)
                        else:
                            d.set(field, value)
    
    # ================================================================================================
    # CORE VALIDATION AND SUBMISSION
    # ================================================================================================
    
    def validate(self):
        super().validate()
        self.validate_company_expenses()

    def on_submit(self):
        if self.difference_amount and self.get("multi_expense") == 0:
            frappe.throw(_("Difference Amount must be zero"))
        self.update_payment_requests()
        self.update_payment_schedule()
        self.make_gl_entries()
        self.update_outstanding_amounts()
        self.set_status()

    # ================================================================================================
    # GL ENTRIES - Party and Bank Accounts
    # ================================================================================================
    
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

    # ================================================================================================
    # MULTI EXPENSE LOGIC
    # ================================================================================================
    # Support for multi-expense payment entries where party is not required
    
    def validate_company_expenses(self):
        if self.get("multi_expense") == 1:
            self.flags.ignore_mandatory = True

    def set_missing_values(self):
        """Reuse the upstream flow unless this is a multi-expense payment entry."""
        if self.payment_type == "Internal Transfer" or not self.is_multi_expense():
            super().set_missing_values()
            return

        self.set_payment_account_details()
        self.set_party_account_currency()

    def is_multi_expense(self):
        """Return whether party-specific validation should be skipped."""
        return cint(self.get("multi_expense")) == 1

    def set_payment_account_details(self):
        """Populate account metadata needed by exchange-rate and GL logic."""
        if self.paid_from and (
            not self.paid_from_account_currency
            or not self.paid_from_account_balance
            or not self.paid_from_account_type
        ):
            acc = get_account_details(self.paid_from, self.posting_date, self.cost_center)
            self.paid_from_account_currency = acc.account_currency
            self.paid_from_account_balance = acc.account_balance
            self.paid_from_account_type = acc.account_type

        if self.paid_to and (
            not self.paid_to_account_currency
            or not self.paid_to_account_balance
            or not self.paid_to_account_type
        ):
            acc = get_account_details(self.paid_to, self.posting_date, self.cost_center)
            self.paid_to_account_currency = acc.account_currency
            self.paid_to_account_balance = acc.account_balance
            self.paid_to_account_type = acc.account_type

    def set_party_account_currency(self):
        """Mirror ERPNext's party-account currency selection for the active direction."""
        self.party_account_currency = (
            self.paid_from_account_currency
            if self.payment_type == "Receive"
            else self.paid_to_account_currency
        )

    def validate_mandatory(self):
        if self.get("multi_expense") == 0:
            super().validate_mandatory()

    def build_gl_map(self):
        if self.payment_type in ("Receive", "Pay") and not self.get("party_account_field"):
            self.setup_party_account_field()
            
        self.set_transaction_currency_and_rate()

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


# ====================================================================================================
# OPTIMA HR INTEGRATION - Helper Functions
# ====================================================================================================
# These functions provide support for Optima HR custom doctypes in Payment Entry references
# - Leave Dues: Employee leave encashment/settlement
# - End of Service Benefits: Employee gratuity and end of service calculations

@frappe.whitelist()
def get_payment_reference_details(
    reference_doctype, reference_name, party_account_currency, party_type=None, party=None
):
    """Get reference details supporting optima_hr doctypes"""
    if HAS_HRMS and reference_doctype in HRMS_EMPLOYEE_REFERENCE_DOCTYPES:
        return get_reference_details_for_employee(
            reference_doctype, reference_name, party_account_currency
        )

    if HAS_OPTIMA_HR and reference_doctype in OPTIMA_EMPLOYEE_REFERENCE_DOCTYPES:
        return get_reference_details_for_optima(reference_doctype, reference_name, party_account_currency)

    return get_reference_details(
        reference_doctype, reference_name, party_account_currency, party_type, party
    )


def get_reference_details_for_optima(reference_doctype, reference_name, party_account_currency):
    """Get reference details for optima_hr doctypes"""
    total_amount = outstanding_amount = exchange_rate = None
    ref_doc = frappe.get_doc(reference_doctype, reference_name)
    company_currency = ref_doc.get("company_currency") or get_company_currency(ref_doc.company)
    total_amount, exchange_rate = get_total_amount_and_exchange_rate(
        ref_doc, party_account_currency, company_currency
    )

    if reference_doctype == "Leave Dues":
        outstanding_amount = flt(ref_doc.total_dues_amount) - flt(ref_doc.paid_amount)
    elif reference_doctype == "End of Service Benefits":
        outstanding_amount = flt(ref_doc.final_result) - flt(ref_doc.paid_amount)

    return frappe._dict(
        {
            "due_date": ref_doc.get("posting_date"),
            "total_amount": flt(total_amount),
            "outstanding_amount": flt(outstanding_amount),
            "exchange_rate": flt(exchange_rate),
        }
    )


def get_total_amount_and_exchange_rate(ref_doc, party_account_currency, company_currency):
    """Get total amount and exchange rate for optima_hr doctypes"""
    total_amount = exchange_rate = None

    if ref_doc.doctype == "Leave Dues":
        total_amount = ref_doc.total_dues_amount
    elif ref_doc.doctype == "End of Service Benefits":
        total_amount = ref_doc.final_result

    if not exchange_rate:
        # Get the exchange rate from the original ref doc
        # or get it based on the posting date of the ref doc.
        exchange_rate = ref_doc.get("conversion_rate") or get_exchange_rate(
            party_account_currency, company_currency, ref_doc.posting_date
        )

    return total_amount, exchange_rate


# ====================================================================================================
# REGIONAL CUSTOMIZATIONS
# ====================================================================================================

@erpnext.allow_regional
def add_regional_gl_entries(gl_entries, doc):
    return
