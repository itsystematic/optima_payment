// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Guarantee-BG Report"] = {
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
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "bank_guarantee_status",
			label: __("Bank Guarantee Status"),
			fieldtype: "Select",
			options: "\nNew\nExists\nIssued\nReturned\nExpired\nExtended\nLost",
		},
		{
			fieldname: "reference_doctype",
			label: __("Reference DocType"),
			fieldtype: "Select",
			options: "\nSales Order\nPurchase Order",
		},
		{
			fieldname: "reference_docname",
			label: __("Reference Docname"),
			fieldtype: "Dynamic Link",
			options: "reference_doctype",
			depends_on: "eval: doc.reference_doctype",
			get_options: () => frappe.query_report.get_filter_value("reference_doctype"),
			get_query: () => ({ filters: { docstatus: 1 } }),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
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
			depends_on: "eval: doc.reference_doctype == 'Purchase Order'",
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
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "bank_guarantee_status" && data.bank_guarantee_status) {
			const color = optima_payment.utils.bank_guarantee_status_colors[data.bank_guarantee_status] || "gray";
			value = `<span class="indicator-pill ${color}">${data.bank_guarantee_status}</span>`;
		}

		return value;
	},
};
