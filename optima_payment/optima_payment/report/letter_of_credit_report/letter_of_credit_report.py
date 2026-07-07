# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.builder import MySQLQueryBuilder
from pypika.functions import Concat



def execute(filters=None):
    columns = get_coloums(filters or {})
    data = get_data(filters)

    return columns, data


def get_data(filters: dict) -> list[dict]:

    query = get_query()
    query = get_conditions(filters, query)

    result = query.run(as_dict=True)
    return result


def get_query() -> MySQLQueryBuilder:
    letter_of_credit = frappe.qb.DocType("Letter of Credit")
    query = (
        frappe.qb.from_(letter_of_credit)
        .select(
            letter_of_credit.bank.as_("bank"),
            letter_of_credit.name.as_("name"),
            letter_of_credit.remarks.as_("remarks"),
            letter_of_credit.project.as_("project"),
            letter_of_credit.customer.as_("customer"),
            letter_of_credit.supplier.as_("supplier"),
            letter_of_credit.end_date.as_("end_date"),
            letter_of_credit.amount.as_("grand_amount"),
            letter_of_credit.start_date.as_("start_date"),
            letter_of_credit.net_amount.as_("net_amount"),
            letter_of_credit.cost_center.as_("cost_center"),
            letter_of_credit.bank_amount.as_("bank_amount"),
            letter_of_credit.posting_date.as_("posting_date"),
            letter_of_credit.new_end_date.as_("new_end_date"),
            letter_of_credit.lc_category.as_("lc_category"),
            letter_of_credit.facility_amount.as_("facility_amount"),
            letter_of_credit.reference_docname.as_("reference_docname"),
            Concat(letter_of_credit.bank_rate_, " %").as_("bank_rate_"),  # Append '%' to bank_rate_
            letter_of_credit.reference_doctype.as_("reference_doctype"),
            letter_of_credit.banking_facilities.as_("banking_facilities"),
            letter_of_credit.lc_status.as_("lc_status"),
            letter_of_credit.lc_number.as_("lc_number"),
            letter_of_credit.lc_amount.as_("lc_amount"),
            Concat(letter_of_credit.facilities_rate_, " %").as_("facilities_rate_"),
            Concat(letter_of_credit.lc_percent, " %").as_("lc_percent"),
        )
        .where(letter_of_credit.docstatus == 1)
    )

    return query


def get_conditions(filters: dict, query: list[dict]) -> MySQLQueryBuilder:
    letter_of_credit = frappe.qb.DocType("Letter of Credit")

    if filters.get("from_date") and filters.get("to_date"):
        query = query.where(
            letter_of_credit.posting_date.between(filters.from_date, filters.to_date)
        )

    if filters.get("lc_status"):
        query = query.where(
            letter_of_credit.lc_status == filters.lc_status
        )

    if filters.get("reference_docname"):
        query = query.where(
            letter_of_credit.reference_docname == filters.reference_docname
        )

    if filters.get("reference_doctype"):
        query = query.where(
            letter_of_credit.reference_doctype == filters.reference_doctype
        )

    if filters.get("project"):
        query = query.where(letter_of_credit.project == filters.project)

    if filters.get("customer"):
        query = query.where(letter_of_credit.customer == filters.customer)

    if filters.get("supplier"):
        query = query.where(letter_of_credit.supplier == filters.supplier)

    if filters.get("lc_category"):
        query = query.where(letter_of_credit.lc_category == filters.lc_category)

    if filters.get("banking_facilities"):
        query = query.where(
            letter_of_credit.banking_facilities == filters.banking_facilities)

    if filters.get("cost_center"):
        query = query.where(letter_of_credit.cost_center == filters.cost_center)

    if filters.get("lc_number"):
        query = query.where(
            letter_of_credit.lc_number == filters.lc_number
        )

    if filters.get("bank"):
        query = query.where(letter_of_credit.bank == filters.bank)

    return query


def get_coloums(filters: dict) -> list[dict]:
    # reference_doctype is "Sales Order" (customer) or "Purchase Order" (supplier) -
    # the two fields are mutually exclusive per row, so drop whichever doesn't apply
    # to the chosen filter. Show both when no reference_doctype filter is set.
    reference_doctype = filters.get("reference_doctype")

    columns = [
        {
            "fieldname": "posting_date",
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "fieldname": "name",
            "label": _("Name"),
            "fieldtype": "Link",
            "options": "Letter of Credit",
            "width": 200,
        },
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200,
        },
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 200,
        },
        {
            "fieldname": "reference_doctype",
            "label": _("Reference DocType"),
            "width": 110,
        },
        {
            "fieldname": "reference_docname",
            "label": _("Reference Document Name"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "start_date",
            "label": _("Start Date"),
            "fieldtype": "Date",
        },
        {
            "fieldname": "end_date",
            "label": _("End Date"),
            "fieldtype": "Date",
        },
        {
            "fieldname": "new_end_date",
            "label": _("New End Date"),
            "fieldtype": "Date",
        },
        {
            "fieldname": "lc_status",
            "label": _("Letter of Credit Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "project",
            "label": _("Project"),
            "fieldtype": "Link",
            "options": "Project",
            "width": 120,
        },
        {
            "fieldname": "cost_center",
            "label": _("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center",
        },
        {
            "fieldname": "lc_category",
            "label": _("Letter of Credit Category"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "bank",
            "label": _("Bank"),
            "fieldtype": "Link",
            "options": "Bank",
        },
        {
            "fieldname": "lc_number",
            "label": _("Letter of Credit Number"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "banking_facilities",
            "label": _("Bank Facilities"),
            "fieldtype": "Data",
        },
        {
            "fieldname": "net_amount",
            "label": _("Net Amount"),
            "fieldtype": "Currency",
        },
        {
            "fieldname": "grand_amount",
            "label": _("Grand Amount"),
            "fieldtype": "Currency",
        },
        {
            "fieldname": "lc_percent",
            "label": _("Letter of Credit Percent"),
            "fieldtype": "Percent",
            "width": 70
        },
        {
            "fieldname": "lc_amount",
            "label": _("Letter of Credit Amount"),
            "fieldtype": "Currency",
            "width": 70
        },
        {
            "fieldname": "bank_rate_",
            "label": _("Bank Rate (%)"),
            "fieldtype": "Percent",
            "width": 70
        },
        {
            "fieldname": "bank_amount",
            "label": _("Bank Amount"),
            "fieldtype": "Currency"
        },
        {
            "fieldname": "facilities_rate_",
            "label": _("Facilities Rate (%)"),
            "fieldtype": "Percent",
            "width": 70
        },
        {
            "fieldname": "facility_amount",
            "label": _("Facilities Amount"),
            "fieldtype": "Currency",
            "width": 70
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Data"
        },
    ]

    if reference_doctype == "Sales Order":
        columns = [c for c in columns if c["fieldname"] != "supplier"]
    elif reference_doctype == "Purchase Order":
        columns = [c for c in columns if c["fieldname"] != "customer"]

    return columns
