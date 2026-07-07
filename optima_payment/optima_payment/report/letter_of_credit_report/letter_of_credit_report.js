// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

frappe.query_reports["Letter of Credit Report"] = {
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
			fieldname: "lc_status",
			label: __("Letter of Credit Status"),
			fieldtype: "Select",
			options: "\nNew\nReturned\nLost\nExtend",
		},
		{
			fieldname: "reference_docname",
			label: __("Reference Docname"),
			fieldtype: "Data",
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
			fieldname: "lc_category",
			label: __("Letter of Credit Category"),
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
			fieldname: "lc_number",
			label: __("Letter of Credit Number"),
			fieldtype: "Data",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "lc_status" && data.lc_status) {
			const color = optima_payment.utils.lc_status_colors[data.lc_status] || "gray";
			value = `<span class="indicator-pill ${color}">${data.lc_status}</span>`;
		}

		return value;
	},
};
