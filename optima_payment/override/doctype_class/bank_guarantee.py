

import frappe
from erpnext.accounts.general_ledger import make_entry, make_gl_entries
from erpnext import get_default_company 
from erpnext.accounts.utils import get_fiscal_years
from frappe.utils import formatdate
from frappe import _
from erpnext.utilities.regional import temporary_flag
from erpnext.controllers.accounts_controller import update_gl_dict_with_regional_fields 
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions 
from frappe.model.document import Document
import copy

import frappe.utils


class CustomBankGuarantee(Document):
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # self.last_gl_entry_date = None

    def validate(self):
        self.validate_customer_or_supplier()
        self.validate_bank_or_cheque()
        self.validate_company_account()
    
    
    def validate_customer_or_supplier(self):
        if not (self.customer or self.supplier):
            frappe.throw(_("Select the customer or supplier."))
    
    def validate_bank_or_cheque(self):
        if (not self.bank_guarantee_number or not  self.bank_guarantee_number) and self.bank_guarantee_purpose in ['Bank Guarantee' , 'Cheque']: 
            frappe.throw(_("Enter the Bank Guarantee Number or name of the Beneficiary before submittting."))
            
    def validate_company_account(self):
        
        company = self.get_company()
        
        if not company.default_insurance_account:
            frappe.throw(_("Please set the Insurance Account under Company Settings."))
            
        if not company.default_receiving_insurance_account:
            frappe.throw(_("Please set the Receiving Insurance Account under Company Settings."))
            
        if not company.bank_fees_account:
            frappe.throw(_("Please set the Bank Fees Account under Company Settings."))
    
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

    def make_cancel_gl_entries(self):  

        gl_entries = self.get_gl_entries()
        make_gl_entries(gl_entries, cancel=True, merge_entries=False ,update_outstanding="No")
    
    def on_submit(self):
        self.set_status()
        self.make_gl_entryies()
    
    
    def set_status(self):
        if self.bank_guarantee_status == "New" :
            if  self.bank_guarantee_purpose in ['Bank Guarantee' , 'Cheque' , "Cash" , "Deduction"] and self.bg_type == "Providing" :
                self.set("bank_guarantee_status" , "Issued")
            
            elif self.bank_guarantee_purpose in ['Bank Guarantee' , 'Cheque' , "Cash" , "Deduction"] and self.bg_type == "Receiving":
                self.set("bank_guarantee_status" , "Exists")
            
    
    def get_debit_or_credit(self):
        type_debit , type_credit = "debit" , "credit"
        if self.bank_guarantee_status in ["Returned"] :
            type_debit , type_credit = "credit" , "debit"
            
        return type_debit , type_credit

    def get_gl_entries(self) :
        gl_entries = []
        company = self.get_company()
        type_debit , type_credit = self.get_debit_or_credit()
        party , party_type = None , None

        posting_date = self.get_posting_date()
        
        self.make_gl_of_bank_or_cheque_providing(gl_entries , type_debit , type_credit , party , party_type, company, posting_date)
        self.make_gl_of_bank_or_cheque_receiving(gl_entries , type_debit , type_credit , company)
        self.make_gl_of_cash_providing(gl_entries , type_debit , type_credit , company)
        self.make_gl_of_cash_receiving(gl_entries , type_debit , type_credit , company)
        self.make_gl_of_deduction_providing(gl_entries , type_debit , type_credit , company)
        self.make_gl_of_deduction_receiving(gl_entries , type_debit , type_credit , company)
        
        return gl_entries
    def make_gl_entryies(self):
    
        gl_entries = self.get_gl_entries()
        make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")

    
    
    def make_gl_of_bank_or_cheque_providing(self ,gl_entries , type_debit , type_credit , party , party_type, company, posting_date):
        if self.bank_guarantee_purpose in ['Bank Guarantee' , 'Cheque'] and self.bg_type == "Providing" :                

            
            self.make_row_in_gl(
                account= self.bank_guarantee_account   if self.bank_guarantee_account  else  company.default_insurance_account ,
                credit_or_debit=type_debit ,
                amount= self.bank_amount ,
                party= self.customer if self.customer else self.supplier ,
                party_type= "Customer" if self.customer else "Supplier" ,
                cost_center = self.cost_center ,
                gl_entries=gl_entries,
                posting_date = posting_date
            )
            
            self.make_row_in_gl(posting_date = posting_date, account=self.account ,credit_or_debit=type_credit ,amount= self.bank_amount ,party= party , party_type = party_type,gl_entries= gl_entries)
            
            if self.bank_guarantee_status != "Returned" and self.issue_commission :
                self.make_row_in_gl(
                    account=company.bank_fees_account ,
                    credit_or_debit=type_debit ,
                    party= party ,
                    party_type = party_type ,
                    amount= self.issue_commission_amount,
                    cost_center = self.cost_center,
                    gl_entries= gl_entries,
                    posting_date = posting_date,
                    against = self.account
                )
                self.make_row_in_gl(
                    account=self.account ,
                    credit_or_debit=type_credit ,
                    amount= self.issue_commission_amount ,
                    party= party ,
                    party_type = party_type,
                    gl_entries= gl_entries,
                    posting_date = posting_date,
                    against = company.bank_fees_account
                )
            
    
    def make_gl_of_bank_or_cheque_receiving(self , gl_entries , type_debit , type_credit , company):
        if self.bank_guarantee_purpose in ['Bank Guarantee' , 'Cheque'] and self.bg_type == "Receiving" : 

            self.make_row_in_gl(
                account=company.default_receiving_insurance_account ,
                credit_or_debit=type_debit ,
                amount=self.amount ,
                party= self.customer ,
                party_type= "Customer" ,
                gl_entries= gl_entries
            )
            self.make_row_in_gl(
                account= self.bank_guarantee_account or  company.default_insurance_account ,
                credit_or_debit=type_credit ,
                amount= self.amount ,
                party= self.customer ,
                party_type= "Customer" ,
                gl_entries=gl_entries
            ) 
            
    
    def make_gl_of_cash_providing(self , gl_entries , type_debit , type_credit , company):
        if self.bank_guarantee_purpose == "Cash" and self.bg_type == "Providing"  :
            
            self.make_row_in_gl(
                account= self.bank_guarantee_account   if self.bank_guarantee_account  else  company.default_insurance_account ,
                credit_or_debit=type_debit ,
                amount=self.amount ,
                party= self.supplier ,
                party_type="Supplier" ,
                gl_entries= gl_entries 
            )
            self.make_row_in_gl(
                account=company.default_cash_account ,
                credit_or_debit=type_credit ,
                amount= self.amount ,
                gl_entries=gl_entries
            ) 
    
    def make_gl_of_cash_receiving(self , gl_entries , type_debit , type_credit , company):
        if self.bank_guarantee_purpose == "Cash" and self.bg_type == "Receiving"  :
            self.make_row_in_gl(account=company.default_cash_account ,credit_or_debit=type_debit ,amount= self.amount , party=self.customer ,party_type= "Customer" ,gl_entries= gl_entries )
            self.make_row_in_gl(account=company.default_receiving_insurance_account ,credit_or_debit=type_credit ,amount= self.amount , party=self.customer , party_type="Customer" ,gl_entries= gl_entries) 
            
    
    def make_gl_of_deduction_providing(self , gl_entries , type_debit , type_credit , company):
        if self.bank_guarantee_purpose == "Deduction" and self.bg_type == "Providing"  :
            self.make_row_in_gl(account=company.default_payable_account ,credit_or_debit=type_debit ,amount= self.amount ,party= self.supplier , party_type="Supplier" ,gl_entries= gl_entries)
            self.make_row_in_gl(account= company.default_receiving_insurance_account ,credit_or_debit=type_credit ,amount= self.amount , party=self.supplier ,party_type= "Supplier" ,gl_entries=  gl_entries ) 
        
    def make_gl_of_deduction_receiving(self , gl_entries , type_debit , type_credit , company):
        if self.bank_guarantee_purpose == "Deduction" and self.bg_type == "Receiving"  :
            self.make_row_in_gl(
                account= self.bank_guarantee_account   if self.bank_guarantee_account  else  company.default_insurance_account ,
                credit_or_debit=type_debit ,
                amount=self.amount ,
                party= self.customer ,
                party_type= "Customer" ,
                gl_entries=gl_entries
            )
            self.make_row_in_gl(account=company.default_receivable_account ,credit_or_debit=type_credit ,amount= self.amount ,party= self.customer , party_type="Customer" ,gl_entries= gl_entries ) 

    def get_gl_dict(self, args, account_currency=None, item=None):

        """this method populates the common properties of a gl entry record"""
        
        posting_date = self.get_posting_date()

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
                # "posting_date": posting_date,
                "fiscal_year": fiscal_year,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "remarks": self.get("remarks") or self.get("remark"),
                "debit": 0,
                "credit": 0,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": 0,
                "is_opening": self.get("is_opening") or "No",
                "party_type": None,
                "party": None,
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
        
        # if not account_currency:
        #     account_currency = get_account_currency(gl_dict.account)

        return gl_dict
    
    
    def make_row_in_gl(
            
        self, 
        account,credit_or_debit,amount, party:str = None ,
        party_type:str = None ,cost_center:str = None ,
        gl_entries:list =[] ,
        posting_date=None,
        against = None ,
        *args , **kwargs
    ) : 
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": account ,
                    "party_type": party_type,
                    "party": party ,
                    credit_or_debit: amount,
                    credit_or_debit + "_in_account_currency": amount , 
                    "project": self.project ,
                    "cost_center": cost_center,
                    "posting_date" : posting_date,
                    "against" : against
                },
        ))
        
    @frappe.whitelist()    
    def bank_guarantee_return(self , returned_date) :
        recent_transaction_date = self.get_recent_transactoin_date()

        returned_date = frappe.utils.getdate(returned_date)
        # ensure extend date is after posting date
        if returned_date < recent_transaction_date :
            frappe.throw(_("Return date cannot be before posting date"))

        gl_entries = self.get_gl_entries()
        self.make_reverse_gl_entries(gl_entries, adv_adj=False, date = returned_date)

        self.update_fields_dict({"bank_guarantee_status" : "Returned" ,"returned_date" : returned_date })
        
    def update_fields_dict(self, dict_updated):
        frappe.db.set_value("Bank Guarantee", self.name , dict_updated , update_modified=True)
        frappe.db.commit()
        self.reload()
    

    @frappe.whitelist()
    def make_extend_action(self ,amount ,end_date ,days ,extend_to_date, has_commission) :
        last_gl_entry_date = self.get_recent_transactoin_date()
        # frappe.log(last_gl_entry_date)


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
    
    
    def make_gl_entry_of_extend(self, extend_to_date, amount) :
        gl_entries = []
        if self.bank_guarantee_purpose == 'Bank Guarantee' and self.bg_type == "Providing" :     
            company = self.get_company()
            self.make_row_in_gl(
                account=company.bank_fees_account ,
                credit_or_debit="debit" ,
                amount= amount ,
                cost_center = self.cost_center,
                gl_entries= gl_entries,
                posting_date = extend_to_date
            )
            self.make_row_in_gl(
                account= self.account if self.account else company.default_bank_account ,
                credit_or_debit="credit" ,
                amount= amount ,
                cost_center= self.cost_center,
                gl_entries= gl_entries,
                posting_date = extend_to_date
            )
            make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")
        
    @frappe.whitelist() 
    def make_loss_action(self , loss_date) :
        """
            reverse existing gls, and make new gls
        """
        # ensure loss date is after posting date
        recent_transaction_date = self.get_recent_transactoin_date()

        loss_date = frappe.utils.getdate(loss_date)
        if loss_date < recent_transaction_date :
            frappe.throw(_("Loss date cannot be before posting date"))

        company = self.get_company()
        gl_entries = self.get_gl_entries()

        self.make_reverse_gl_entries(gl_entries, adv_adj=False,   date = loss_date)

        gl_entries = []
        self.make_row_in_gl(
            account= company.default_receivable_account , 
            credit_or_debit="debit" ,
            party= self.customer ,
            party_type = "Customer" ,
            amount= self.bank_guarantee_amount,
            cost_center = self.cost_center,
            posting_date = loss_date ,
            gl_entries= gl_entries
        )
        self.make_row_in_gl(
            account=self.account ,
            credit_or_debit="credit" ,
            amount= self.bank_guarantee_amount ,
            party= None ,
            party_type = None,
            posting_date = loss_date ,
            # cost_center= self.cost_center,
            gl_entries= gl_entries
        )
        
        make_gl_entries(gl_entries, cancel=False, merge_entries=False ,update_outstanding="No")
        self.update_fields_dict({ "bank_guarantee_status" : "Lost" })
    
    
    def get_company(self) :
        company = get_default_company()
        
        if self.company  :
            company = self.company
            
        return frappe.get_doc("Company" , company)
    
    
    def on_trash(self) :
        
        self.remove_gl_entries()
        self.remove_stock_ledger()
        self.remove_payment_ledger_entry()
    
    def remove_gl_entries(self) :
        
        frappe.db.sql(
                "delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s", (self.doctype, self.name)
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

    def get_recent_transactoin_date(self) :
        voucher_no = self.name
        d = frappe.get_all("GL Entry", filters={'voucher_no': voucher_no}, pluck='posting_date',order_by='posting_date desc', limit=1)
        recent_transaction_date = d[0]

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
    
    def make_reverse_gl_entries(self,gl_entries=None, adv_adj=False, date = None):
        """
        Get original gl entries of the voucher
        and make reverse gl entries by swapping debit and credit
        """

        gl_entries = gl_entries or []
        if gl_entries:
            for entry in gl_entries:
                if entry.get("against"): # bank commiosion do net return, skip it's gls, to aviod reversing
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

@frappe.whitelist()
def get_reference_docname(*args, **kwargs):
    bank_guarantee_sales_orders = frappe.get_list(
                                doctype = "Bank Guarantee" ,
                                filters = {"bank_guarantee_status": ["not in", ["Lost", "Returned"]]
                                        # "distinct": "bank_guarantee_status"
                                        } , 
                                pluck ="reference_docname" 
                            )   


    return frappe.db.sql(
                        """
                            SELECT `tabSales Order`.name FROM `tabSales Order`
                            WHERE `tabSales Order`.name NOT IN (%s)
                            ORDER BY `tabSales Order`.creation DESC
                        """
                            % ", ".join(["%s"] * len(bank_guarantee_sales_orders)),
                            tuple(inv for inv in bank_guarantee_sales_orders))


# @frappe.whitelist()
# def revised_get_reference_docname(*args, **kwargs):
#     sales_orders = frappe.qb.DocType("Sales Order")
#     bank_guarantee = frappe.qb.DocType("Bank Guarantee")

#     return (
#         frappe.qb.from_(sales_orders)
#         .select(sales_orders.name)
#         .where(
#             ~sales_orders.name.isin(
#                 frappe.qb.from_(bank_guarantee)
#                 .select(bank_guarantee.reference_docname)
#                 .where(bank_guarantee.bank_guarantee_status.notin(["Lost", "Returned"]))
#             )
#         )
#         .order_by(sales_orders.creation.desc())
#         .run()
#     )
