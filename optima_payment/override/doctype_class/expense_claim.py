
import frappe 
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account



class CustomExpenseClaim(ExpenseClaim):
    """_summary_

    Args:
        ExpenseClaim (_type_): _description_
    """
        
    def get_gl_entries(self):
        gl_entry = []
        self.validate_account_details()

        # payable entry
        if self.grand_total:
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": self.payable_account,
                        "credit": self.grand_total,
                        "credit_in_account_currency": self.grand_total,
                        "against": ",".join([d.default_account for d in self.expenses]),
                        "party_type": "Employee",
                        "party": self.employee,
                        "against_voucher_type": self.doctype,
                        "against_voucher": self.name,
                        "cost_center": self.cost_center,
                        "project": self.project,
                    },
                    item=self,
                )
            )
        
        # expense entries
        for data in self.expenses:

            if data.get("purchase_invoice") :
                purchase = frappe.get_doc("Purchase Invoice" , data.purchase_invoice)

            gl_entry.append(
                self.get_gl_dict(
                    {
                        # "account": data.default_account if not data.get("purchase_invoice") else self.payable_account ,
                        "account": data.default_account  ,
                        "debit": data.sanctioned_amount,
                        "debit_in_account_currency": data.sanctioned_amount,
						"party_type" : "Supplier" if data.get("purchase_invoice") else "",
						"party" : purchase.get("supplier") if data.get("purchase_invoice") else "",
                        "against": self.employee,
                        "cost_center": data.get("cost_center") or self.get("cost_center"),
                        "against_voucher_type" : "Purchase Invoice" if data.get("purchase_invoice") else None ,
                        "against_voucher" : data.get("purchase_invoice") if data.get("purchase_invoice") else None ,
                    },
                    item=data,
                )
            )

        for data in self.advances:
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": data.advance_account,
                        "credit": data.allocated_amount,
                        "credit_in_account_currency": data.allocated_amount,
                        "against": ",".join([d.default_account for d in self.expenses]),
                        "party_type": "Employee",
                        "party": self.employee,
                        "against_voucher_type": "Employee Advance",
                        "against_voucher": data.employee_advance,
                    }
                )
            )

        self.add_tax_gl_entries(gl_entry)

        if self.is_paid and self.grand_total:
            # payment entry
            payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": payment_account,
                        "credit": self.grand_total,
                        "credit_in_account_currency": self.grand_total,
                        "against": self.employee,
                    },
                    item=self,
                )
            )

            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": self.payable_account,
                        "party_type": "Employee",
                        "party": self.employee,
                        "against": payment_account,
                        "debit": self.grand_total,
                        "debit_in_account_currency": self.grand_total,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                    },
                    item=self,
                )
            )

        return gl_entry
