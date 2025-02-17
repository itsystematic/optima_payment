// Copyright (c) 2025, IT Systematic and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Guarantee Report"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "bank_guarantee_status",
			label: __("Bank Guarantee Status"),
			fieldtype: "Select",
			options: "\nNew\nReturned\nLost\nExtend",
			default: "New",
		},
		{
			fieldname: "reference_docname",
			label: __("Reference Docname"),
			fieldtype: "Link",
			options: "Sales Order",
		},
		{
			fieldname: "reference_doctype",
			label: __("Reference DocType"),
			fieldtype: "Link",
			options: "DocType",
			default: "Sales Order",
			read_only: 1,
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "guarantee_type",
			label: __("Guarantee Type"),
			fieldtype: "Select",
			options: "\nInitial\nAdvanced Payment\nFinal",
			default: "Initial",
		},
		{
			fieldname: "banking_facilities",
			label: __("Bank Facilities"),
			fieldtype: "Select",
			options: "\nWithout Facilities\nwith Facilities",
			default: "",
		},
		{
			fieldname: "bank_guarantee_number",
			label: __("Bank Guarantee Number"),
			fieldtype: "Data",
		},
	]
};
