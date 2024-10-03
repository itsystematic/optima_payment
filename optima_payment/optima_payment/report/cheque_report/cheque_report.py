# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_dashboard_chart(data)
	return columns, data , None , None


def get_columns(filters) :
	columns = [
		{
			"fieldname": "name",
			"label": _("Payment Entry"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 220
		},
		{
			"fieldname": "reference_no",
			"label": _("Cheque No"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname": "reference_date",
			"label": _("Cheque Date"),
			"fieldtype": "Date",
			"width": 130
		},
		{
			"fieldname" : "cheque_status",
			"label": _("Cheque Status"),
			"fieldtype": "Data",
			"width": 200
		},
		{"label": _("Party Type"), "fieldname": "party_type", "width": 110},
		{"label": _("Party"), "fieldname": "party", "width": 250},
		{
			"label": _("Bank Name"),
			"fieldname": "bank_name",
			"fieldtype": "Link",
			"options" : "Bank" ,
			"width": 150
		},
		{
			"label": _("Payee Name"),
			"fieldname": "payee_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 140
		}
	]

	return columns


def get_conditions(filters) :
	conditions = ""

	if filters.get("from_date") and filters.get("to_date"):
		conditions += " AND pe.reference_date BETWEEN '{0}' AND '{1}' ".format(filters.get("from_date"), filters.get("to_date"))

	if filters.get("company"):
		conditions += " AND pe.company = '{0}' ".format(filters.get("company"))

	if filters.get("cheque_status"):
		conditions += " AND pe.cheque_status = '{0}' ".format(filters.get("cheque_status"))

	if filters.get("reference_no"):
		conditions += " AND pe.reference_no = '{0}' ".format(filters.get("reference_no"))

	if filters.get("party_type") and filters.get("party"):
		conditions += " AND pe.party_type = '{0}' AND pe.party = '{1}' ".format(filters.get("party_type"), filters.get("party"))

	if filters.get("bank_name"):
		conditions += " AND pe.bank_name = '{0}' ".format(filters.get("bank_name"))


	return conditions

def get_data(filters) :

	conditions = get_conditions(filters)

	sql_query = frappe.db.sql(""" 
		SELECT 
			pe.name,
			pe.reference_no,
			pe.reference_date,
			pe.cheque_status,
			pe.party_type,
			pe.party,
			pe.bank_name ,
			pe.payee_name , 
			pe.paid_amount
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabMode of Payment` mop on mop.name = pe.mode_of_payment
		WHERE pe.docstatus = 1 
			AND mop.type = "Cheque"

			{conditions}
	""".format(conditions=conditions), as_dict=1)

	return sql_query


def get_dashboard_chart(data) :

	pass