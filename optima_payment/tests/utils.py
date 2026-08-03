"""Shared test factories for Optima Payment.

Provides reusable, defensive (frappe.db.exists/get_value-guarded) builders for
the fixtures Optima Payment's integration tests need: Payment Entry overrides,
and the full chain required to submit a Bank Guarantee-BG (Optima Payment
Setting, Bank, Account, Cost Center, Project, Customer/Supplier, and a
reference Sales/Purchase Order with its own taxes table pre-populated to dodge
this site's KSA/ZATCA mandatory-field customizations). Tests import these
factories instead of constructing documents inline.
"""

import frappe
import erpnext
from frappe.utils import add_days, nowdate

from optima_payment.override.doctype_class.payment_entry import CustomPaymentEntry
from optima_payment.optima_payment.doctype.bank_guarantee_bg.bank_guarantee_bg import BankGuaranteeBG
from optima_payment.optima_payment.doctype.letter_of_credit.letter_of_credit import LetterofCredit


# ====================================================================================================
# PAYMENT ENTRY FACTORIES


def get_payment_entry_naming_series() -> str:
    """Return the default naming series used by Payment Entry tests."""
    return frappe.get_meta("Payment Entry").get_field("naming_series").default or "PAY-.FY.-"


def get_payment_entry_account(company: str | None = None) -> str:
    """Pick a bank or cash account that Payment Entry is allowed to use."""
    company = company or erpnext.get_default_company()
    account = frappe.get_list(
        "Account",
        filters={"company": company, "account_type": ("in", ["Bank", "Cash"]), "is_group": 0},
        pluck="name",
        reference_doctype="Payment Entry",
        limit=1,
    )

    if not account:
        frappe.throw(f"No bank or cash account is permitted for Payment Entry in company {company}")

    return account[0]


def make_payment_entry(
    *,
    multi_expense: int = 0,
    company: str | None = None,
    payment_account: str | None = None,
    naming_series: str | None = None,
) -> CustomPaymentEntry:
    """Build a minimal Payment Entry document for override-focused tests."""
    company = company or erpnext.get_default_company()
    payment_account = payment_account or get_payment_entry_account(company)
    naming_series = naming_series or get_payment_entry_naming_series()

    pe = frappe.new_doc("Payment Entry")
    pe.update(
        {
            "naming_series": naming_series,
            "payment_type": "Pay",
            "posting_date": nowdate(),
            "company": company,
            "multi_expense": multi_expense,
            "paid_from": payment_account,
            "paid_amount": 100,
            "received_amount": 100,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "base_paid_amount": 100,
            "base_received_amount": 100,
        }
    )
    return pe


# ====================================================================================================
# ACCOUNT TREE / COMPANY FIXTURES
# Shared financial fixtures (account, bank, cost center, project) reused across
# Bank Guarantee-BG and Payment Entry factories below.


def get_or_create_account(
    account_name: str, company: str, root_type: str, account_type: str | None = None
) -> str:
    """Find or create a leaf Account of the given root_type under company's account tree."""
    existing = frappe.db.get_value("Account", {"account_name": account_name, "company": company}, "name")
    if existing:
        return existing

    parent_account = frappe.db.get_value(
        "Account", {"company": company, "root_type": root_type, "is_group": 1}, "name"
    )
    if not parent_account:
        frappe.throw(f"No {root_type} group account found for company {company}")

    account = frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": account_name,
            "parent_account": parent_account,
            "company": company,
            "is_group": 0,
            "account_type": account_type,
        }
    )
    account.insert(ignore_permissions=True)
    return account.name


def get_or_create_bank(bank_name: str = "Optima Test Bank") -> str:
    """Find or create the Bank used by Bank Guarantee-BG tests."""
    if not frappe.db.exists("Bank", bank_name):
        frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(ignore_permissions=True)
    return bank_name


def get_or_create_cost_center(company: str) -> str:
    """Return an existing leaf Cost Center for company."""
    cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
    if not cost_center:
        frappe.throw(f"No cost center found for company {company}")
    return cost_center


def get_or_create_project(company: str, project_name: str = "Optima Test Project") -> str:
    """Find or create a Project for company."""
    name = frappe.db.get_value("Project", {"project_name": project_name, "company": company}, "name")
    if name:
        return name

    project = frappe.get_doc(
        {"doctype": "Project", "project_name": project_name, "company": company}
    )
    project.insert(ignore_permissions=True)
    return project.name


# ====================================================================================================
# PARTY FIXTURES


def get_or_create_customer(customer_name: str = "Optima Test Customer") -> str:
    """Find or create the Customer used as the default Sales Order party in tests."""
    if not frappe.db.exists("Customer", customer_name):
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
        frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_group": customer_group,
                # customer_type=Individual dodges KSA site customizations that make
                # registration_type / registration_value / tax_id mandatory for Companies.
                "customer_type": "Individual",
                # Site-specific mandatory custom field; the key is ignored where it doesn't exist.
                "customer_name_in_arabic": customer_name,
            }
        ).insert(ignore_permissions=True)
    return customer_name


def get_or_create_supplier(supplier_name: str = "Optima Test Supplier") -> str:
    """Find or create the Supplier used as the default Purchase Order party in tests."""
    if not frappe.db.exists("Supplier", supplier_name):
        # KSA sites make tax_id mandatory for local suppliers; prefer an "external" supplier
        # group when the site defines one, otherwise fall back to any leaf group.
        supplier_group = frappe.db.get_value(
            "Supplier Group", {"supplier_group_name": "موردين خارجيين"}, "name"
        ) or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
        # KSA/ZATCA customizations on this site make tax_category mandatory on Supplier.
        tax_category = frappe.db.get_value("Tax Category", {}, "name")
        frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": supplier_name,
                "supplier_group": supplier_group,
                "tax_category": tax_category,
                # Site-specific mandatory custom field; ignored where it doesn't exist.
                "supplier_name_in_arabic": supplier_name,
            }
        ).insert(ignore_permissions=True)
    return supplier_name


# ====================================================================================================
# MODE OF PAYMENT FIXTURE


def get_or_create_mode_of_payment(
    company: str, account: str, mode_name: str = "Optima LC Transfer"
) -> str:
    """Find or create a Mode of Payment whose per-company account maps to ``account``.

    Letter of Credit requires a Mode of Payment (validate_mode_of_payment) and every
    system-generated Payment Entry copies it over, so the mode must have a Mode of
    Payment Account row for this company pointing at a real (Bank/Cash) account.
    """
    if not frappe.db.exists("Mode of Payment", mode_name):
        frappe.get_doc(
            {
                "doctype": "Mode of Payment",
                "mode_of_payment": mode_name,
                "type": "Bank",
                "accounts": [{"company": company, "default_account": account}],
            }
        ).insert(ignore_permissions=True)
        return mode_name

    mop = frappe.get_doc("Mode of Payment", mode_name)
    if not any(row.company == company for row in mop.accounts):
        mop.append("accounts", {"company": company, "default_account": account})
        mop.save(ignore_permissions=True)
    return mode_name


# ====================================================================================================
# ITEM / TAX FIXTURES
# Item.taxes and the order-level taxes table are pre-populated here to dodge this
# site's KSA/ZATCA mandatory-field customizations (see get_item_tax_charge).


def get_or_create_item(item_code: str = "Optima Test Item") -> str:
    """Find or create a non-stock Item usable on both Sales and Purchase Orders."""
    if not frappe.db.exists("Item", item_code):
        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        # KSA/ZATCA customizations on this site make the Item Tax Template table mandatory.
        item_tax_template = frappe.db.get_value("Item Tax Template", {}, "name")
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": item_group,
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "taxes": [{"item_tax_template": item_tax_template}],
            }
        ).insert(ignore_permissions=True)
    return item_code


def get_item_tax_charge() -> tuple[str, float]:
    """Return (account_head, tax_rate) of an existing Item Tax Template's single tax row.

    Used to pre-populate the order's own ``taxes`` table so that ERPNext's
    "Add taxes from item tax template" Accounts Settings option doesn't
    auto-append a Sales/Purchase Taxes and Charges row without a cost_center
    (which this site's customizations make mandatory).
    """
    item_tax_template = frappe.db.get_value("Item Tax Template", {}, "name")
    detail = frappe.db.get_value(
        "Item Tax Template Detail", {"parent": item_tax_template}, ["tax_type", "tax_rate"]
    )
    return detail


# ====================================================================================================
# REFERENCE SALES / PURCHASE ORDERS


def make_reference_sales_order(company: str, customer: str) -> str:
    """Create and submit a minimal Sales Order to use as a Bank Guarantee-BG reference."""
    item = get_or_create_item()
    cost_center = get_or_create_cost_center(company)
    account_head, tax_rate = get_item_tax_charge()
    so = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "company": company,
            "customer": customer,
            "cost_center": cost_center,
            "delivery_date": nowdate(),
            "items": [{"item_code": item, "qty": 1, "rate": 100, "cost_center": cost_center}],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": account_head,
                    "rate": tax_rate,
                    "cost_center": cost_center,
                    "description": account_head,
                }
            ],
        }
    )
    so.insert(ignore_permissions=True)
    so.submit()
    return so.name


def make_reference_purchase_order(company: str, supplier: str) -> str:
    """Create and submit a minimal Purchase Order to use as a Bank Guarantee-BG reference."""
    item = get_or_create_item()
    cost_center = get_or_create_cost_center(company)
    account_head, tax_rate = get_item_tax_charge()
    po = frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "company": company,
            "supplier": supplier,
            "cost_center": cost_center,
            "schedule_date": nowdate(),
            "items": [{"item_code": item, "qty": 1, "rate": 100, "cost_center": cost_center}],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": account_head,
                    "rate": tax_rate,
                    "cost_center": cost_center,
                    "description": account_head,
                }
            ],
        }
    )
    po.insert(ignore_permissions=True)
    po.submit()
    return po.name


# ====================================================================================================
# BANK GUARANTEE-BG FACTORIES


def make_optima_payment_setting(company: str | None = None, **overrides) -> frappe.model.document.Document:
    """Find or create the (unique, per-company) Optima Payment Setting with all
    Bank Guarantee-BG and Letter of Credit accounts populated, so each doctype's
    validate_company_account() passes."""
    company = company or erpnext.get_default_company()

    existing = frappe.db.get_value("Optima Payment Setting", {"company": company}, "name")
    if existing:
        setting = frappe.get_doc("Optima Payment Setting", existing)
        # Backfill any account the persisted setting is missing - a real site may already
        # have an Optima Payment Setting that predates some of these BG/LC account fields.
        missing_account_fields = {
            "bank_guarantee_insurance_account": lambda: get_or_create_account(
                "Optima BG Insurance", company, "Asset"
            ),
            "bank_guarantee_receiving_insurance_account": lambda: get_or_create_account(
                "Optima BG Receiving Insurance", company, "Asset"
            ),
            "bank_guarantee_bank_fees_account": lambda: get_or_create_account(
                "Optima BG Bank Fees", company, "Expense"
            ),
            "bank_guarantee_loss_expense_account": lambda: get_or_create_account(
                "Optima BG Loss Expense", company, "Expense"
            ),
            "lc_insurance_account": lambda: get_or_create_account("Optima LC Insurance", company, "Asset"),
            "lc_receiving_insurance_account": lambda: get_or_create_account(
                "Optima LC Receiving Insurance", company, "Asset"
            ),
            "lc_bank_fees_account": lambda: get_or_create_account("Optima LC Bank Fees", company, "Expense"),
            "lc_loss_expense_account": lambda: get_or_create_account(
                "Optima LC Loss Expense", company, "Expense"
            ),
        }
        dirty = False
        for fieldname, make_value in missing_account_fields.items():
            if not setting.get(fieldname):
                setting.set(fieldname, make_value())
                dirty = True
        if dirty:
            setting.save(ignore_permissions=True)
        return setting

    fields = {
        "company": company,
        "bank_guarantee_insurance_account": get_or_create_account(
            "Optima BG Insurance", company, "Asset"
        ),
        "bank_guarantee_receiving_insurance_account": get_or_create_account(
            "Optima BG Receiving Insurance", company, "Asset"
        ),
        "bank_guarantee_bank_fees_account": get_or_create_account(
            "Optima BG Bank Fees", company, "Expense"
        ),
        "bank_guarantee_loss_expense_account": get_or_create_account(
            "Optima BG Loss Expense", company, "Expense"
        ),
        "lc_insurance_account": get_or_create_account(
            "Optima LC Insurance", company, "Asset"
        ),
        "lc_receiving_insurance_account": get_or_create_account(
            "Optima LC Receiving Insurance", company, "Asset"
        ),
        "lc_bank_fees_account": get_or_create_account(
            "Optima LC Bank Fees", company, "Expense"
        ),
        "lc_loss_expense_account": get_or_create_account(
            "Optima LC Loss Expense", company, "Expense"
        ),
    }
    fields.update(overrides)

    setting = frappe.get_doc({"doctype": "Optima Payment Setting", **fields})
    setting.insert(ignore_permissions=True)
    return setting


def make_bank_guarantee_bg(
    *,
    bg_type: str = "Providing",
    company: str | None = None,
    issue_commission: int = 0,
    do_not_submit: bool = False,
    **overrides,
) -> BankGuaranteeBG:
    """Build a minimally valid Bank Guarantee-BG document for integration tests."""
    company = company or erpnext.get_default_company()
    make_optima_payment_setting(company)

    bank = get_or_create_bank()
    account = get_or_create_account("Optima BG Test Account", company, "Asset", account_type="Bank")
    cost_center = get_or_create_cost_center(company)
    project = get_or_create_project(company)

    if bg_type == "Providing":
        customer = get_or_create_customer()
        reference_doctype = "Sales Order"
        reference_docname = make_reference_sales_order(company, customer)
        party_fields = {"customer": customer}
    else:
        supplier = get_or_create_supplier()
        reference_doctype = "Purchase Order"
        reference_docname = make_reference_purchase_order(company, supplier)
        party_fields = {"supplier": supplier}

    fields = {
        "doctype": "Bank Guarantee-BG",
        "bg_type": bg_type,
        "guarantee_type": "Initial",
        "company": company,
        "posting_date": nowdate(),
        "start_date": nowdate(),
        "validity": 30,
        "end_date": add_days(nowdate(), 29),
        "no_of_extended_days": 0,
        "bank": bank,
        "account": account,
        "cost_center": cost_center,
        "project": project,
        "reference_doctype": reference_doctype,
        "reference_docname": reference_docname,
        "net_amount": 1000,
        "tax_amount": 0,
        "amount": 1000,
        "bank_guarantee_percent": 10,
        "bank_guarantee_amount": 100,
        "bank_rate_": 100,
        "bank_amount": 100,
        "name_of_beneficiary": company,
        "bank_guarantee_number": frappe.generate_hash(length=10),
        "issue_commission": issue_commission,
        "issue_commission_amount": 50 if issue_commission else 0,
    }
    fields.update(party_fields)
    fields.update(overrides)

    doc = frappe.get_doc(fields)
    doc.insert(ignore_permissions=True)

    if not do_not_submit:
        doc.submit()

    return doc


# ====================================================================================================
# LETTER OF CREDIT FACTORIES


def make_letter_of_credit(
    *,
    lc_type: str = "Providing",
    company: str | None = None,
    issue_commission: int = 0,
    do_not_submit: bool = False,
    **overrides,
) -> LetterofCredit:
    """Build a minimally valid Letter of Credit document for integration tests."""
    company = company or erpnext.get_default_company()
    make_optima_payment_setting(company)

    bank = get_or_create_bank()
    account = get_or_create_account("Optima LC Test Account", company, "Asset", account_type="Bank")
    # Explicit collateral account so the generated Payment Entry uses the primary
    # get_payment_entry_accounts() path (self.lc_account) rather than the
    # settings.lc_insurance_account fallback. Pass lc_account=None to exercise the fallback.
    lc_account = get_or_create_account("Optima LC Collateral Account", company, "Asset", account_type="Bank")
    mode_of_payment = get_or_create_mode_of_payment(company, account)
    cost_center = get_or_create_cost_center(company)
    project = get_or_create_project(company)

    if lc_type == "Providing":
        customer = get_or_create_customer()
        reference_doctype = "Sales Order"
        reference_docname = make_reference_sales_order(company, customer)
        party_fields = {"customer": customer}
    else:
        supplier = get_or_create_supplier()
        reference_doctype = "Purchase Order"
        reference_docname = make_reference_purchase_order(company, supplier)
        party_fields = {"supplier": supplier}

    fields = {
        "doctype": "Letter of Credit",
        "lc_type": lc_type,
        "lc_category": "Sight",
        # lc_status has no JSON default; set_status() only promotes it to Issued/Exists
        # when it starts as "New", so seed it here.
        "lc_status": "New",
        "company": company,
        "posting_date": nowdate(),
        "start_date": nowdate(),
        "validity": 30,
        "end_date": add_days(nowdate(), 29),
        "no_of_extended_days": 0,
        # Seed the extend accumulators to 0 so the in-memory doc matches a DB-loaded one
        # (these Currency columns default to 0.0); lc_extend_action increments them.
        "extended_cash_margin_amount": 0,
        "extended_facility_amount": 0,
        "bank": bank,
        "account": account,
        "lc_account": lc_account,
        "mode_of_payment": mode_of_payment,
        "cost_center": cost_center,
        "project": project,
        "reference_doctype": reference_doctype,
        "reference_docname": reference_docname,
        "net_amount": 1000,
        "tax_amount": 0,
        "amount": 1000,
        "lc_percent": 10,
        "lc_amount": 100,
        "bank_rate_": 100,
        "bank_amount": 100,
        "name_of_beneficiary": company,
        "lc_number": frappe.generate_hash(length=10),
        "issue_commission": issue_commission,
        "issue_commission_amount": 50 if issue_commission else 0,
    }
    fields.update(party_fields)
    fields.update(overrides)

    doc = frappe.get_doc(fields)
    doc.insert(ignore_permissions=True)

    if not do_not_submit:
        doc.submit()

    return doc
