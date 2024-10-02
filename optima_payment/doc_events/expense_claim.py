import frappe 
from frappe import _
from frappe.utils import flt

def validate(doc, method):
    validate_total_amount_invoice_equal_total_advances(doc)


def validate_total_amount_invoice_equal_total_advances(doc):
    pass
    # if doc.advances:
    #     total_amount_of_invoices = sum(expense.amount for expense in doc.expenses)
    #     total_allocated_amount_of_advances = sum(advance.allocated_amount for advance in doc.advances)
    #     if total_amount_of_invoices != total_allocated_amount_of_advances:
    #         frappe.throw(_("The Amount Must be same {0}, {1}".format(total_amount_of_invoices, total_allocated_amount_of_advances)))




def calculate_total_amount(doc, method):
    doc.total_claimed_amount = 0
    doc.total_sanctioned_amount = 0
    doc.taxable_amount = 0
    for d in doc.get("expenses"):
        if doc.approval_status == "Rejected":
            d.sanctioned_amount = 0.0
        if d.get("with_vat", 0) == 1:
            doc.taxable_amount += flt(d.sanctioned_amount)

        doc.total_claimed_amount += flt(d.amount)
        doc.total_sanctioned_amount += flt(d.sanctioned_amount)

@frappe.whitelist()
def calculate_taxes(doc, method):
    calculate_total_amount(doc, method)
    doc.total_taxes_and_charges = 0
    for tax in doc.taxes:
        if tax.rate:
            tax.tax_amount = flt(doc.taxable_amount) * flt(tax.rate / 100)

        tax.total = flt(tax.tax_amount) + flt(doc.taxable_amount)
        doc.total_taxes_and_charges += flt(tax.tax_amount)

    doc.grand_total = (
        flt(doc.total_sanctioned_amount)
        + flt(doc.total_taxes_and_charges)
        - flt(doc.total_advance_amount)
    )

@frappe.whitelist()   
def validate_outstanding_amount(purchase_invoice: str = "", amount: float = 0.00) -> dict:
    ref_doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if abs(ref_doc.get("outstanding_amount")) < amount:
        frappe.throw(_("The Amount Must be Smaller Than purchase invoice Amount {}".format(purchase_invoice)))
        
    if ref_doc.get("is_return") == 1:
        frappe.throw(_("Can't Pay Returned Invoice {}".format(purchase_invoice)))

    return ref_doc