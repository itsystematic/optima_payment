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
		},
		{
			fieldname: "reference_docname",
			label: __("Reference Docname"),
			fieldtype: "Data",
			// options: "reference_doctype",
		},
		{
			fieldname: "reference_doctype",
			label: __("Reference DocType"),
			fieldtype: "Select",
			options: "\nPurchase Invoice\nSales Order",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
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
			depends_on: "eval: doc.reference_doctype == 'Sales Order'",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			depends_on: "eval: doc.reference_doctype == 'Purchase Invoice'",
		},
		{
			fieldname: "guarantee_type",
			label: __("Guarantee Type"),
			fieldtype: "Select",
			options: "\nInitial\nAdvanced Payment\nFinal\nFinacial",
		},
		{
			fieldname: "bank",
			label: __("Bank"),
			fieldtype: "Link",
			options: "Bank",
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
