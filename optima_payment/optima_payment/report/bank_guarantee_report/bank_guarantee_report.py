# Copyright (c) 2025, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_coloums()
	data = get_data(filters)

	return columns, data

def get_data(filters: dict) -> list[dict]:
	
	query = get_query()
	query = get_conditions(filters, query)


	result = query.run(as_dict=True)
	return result

def get_query() -> str:
	bank_guarantee = frappe.qb.DocType("Bank Guarantee")
	query = (
		frappe.qb.from_(bank_guarantee)
		.select(
			bank_guarantee.name.as_("name"),
			bank_guarantee.project.as_("project"),
			bank_guarantee.customer.as_("customer"),
			bank_guarantee.end_date.as_("end_date"),
			bank_guarantee.amount.as_("grand_amount"),
			bank_guarantee.bank_rate_.as_("bank_rate_"),
			bank_guarantee.net_amount.as_("net_amount"),
			bank_guarantee.start_date.as_("start_date"),
			bank_guarantee.posting_date.as_("posting_date"),
			bank_guarantee.guarantee_type.as_("guarantee_type"),
			bank_guarantee.facilities_rate_.as_("facilities_rate_"),
			bank_guarantee.reference_docname.as_("reference_docname"),
			bank_guarantee.reference_doctype.as_("reference_doctype"),
			bank_guarantee.banking_facilities.as_("banking_facilities"),
			bank_guarantee.bank_guarantee_status.as_("bank_guarantee_status"),
			bank_guarantee.bank_guarantee_number.as_("bank_guarantee_number"),
			bank_guarantee.bank_guarantee_amount.as_("bank_guarantee_amount"),
			bank_guarantee.bank_guarantee_percent.as_("bank_guarantee_percent"),
		)
		.where(bank_guarantee.docstatus == 1)
	)

	return query

def get_conditions(filters: dict, query: list[dict]) -> str:
	bank_guarantee = frappe.qb.DocType("Bank Guarantee")

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(bank_guarantee.posting_date.between(filters.from_date, filters.to_date))
	
	if filters.get("bank_guarantee_status"):
		query = query.where(bank_guarantee.bank_guarantee_status == filters.bank_guarantee_status)
	
	if filters.get("reference_docname"):
		query = query.where(bank_guarantee.reference_docname == filters.reference_docname)
	
	if filters.get("reference_doctype"):
		query = query.where(bank_guarantee.reference_doctype == filters.reference_doctype)
	
	if filters.get("project"):
		query = query.where(bank_guarantee.project == filters.project)
	
	if filters.get("customer"):
		query = query.where(bank_guarantee.customer == filters.customer)
	
	if filters.get("guarantee_type"):
		query = query.where(bank_guarantee.guarantee_type == filters.guarantee_type)
	
	if filters.get("banking_facilities"):
		query = query.where(bank_guarantee.banking_facilities == filters.banking_facilities)

	if filters.get("bank_guarantee_number"):
		query = query.where(bank_guarantee.bank_guarantee_number == filters.bank_guarantee_number)
	
	return query

def get_coloums() -> list[dict]:
	
	return [
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
			"options": "Bank Guarantee",
			"width": 200
		},
		{
			"fieldname": "bank_guarantee_status",
			"label": _("Bank Guarantee Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "reference_docname",
			"label": _("Reference Docname"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 200
		},
		{
			"fieldname": "reference_doctype",
			"label": _("Reference DocType"),
			"width": 100
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "guarantee_type",
			"label": _("Guarantee Type"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "banking_facilities",
			"label": _("Bank Facilities"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "bank_guarantee_number",
			"label": _("Bank Guarantee Number"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "net_amount",
			"label": _("Net Amount"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "amount",
			"label": _("Grand Amount"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "bank_guarantee_percent",
			"label": _("Bank Guarantee Percent"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "bank_guarantee_amount",
			"label": _("Bank Guarantee Amount"),
			"fieldtype": "Currency",
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
			"fieldname": "bank_rate_",
			"label": _("Bank Rate"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "facilities_rate_",
			"label": _("Facilities Rate"),
			"fieldtype": "Data",
		},
	]