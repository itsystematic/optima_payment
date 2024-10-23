// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.query_reports["Cheque Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Posting Date", "Reference Date"],
			default: ["Reference Date"],
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");

				frappe.query_report.toggle_filter_display("posting_start_date",filter_based_on === "Reference Date");
				frappe.query_report.toggle_filter_display("posting_end_date", filter_based_on === "Reference Date");

				frappe.query_report.toggle_filter_display(
					"reference_start_date",
					filter_based_on === "Posting Date"
				);
				frappe.query_report.toggle_filter_display(
					"reference_end_date",
					filter_based_on === "Posting Date"
				);

				frappe.query_report.refresh();
			}
		},
		{
			fieldname: "posting_start_date",
			label: __("From Posting Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.add_months(frappe.datetime.get_today(), -2),
			depends_on: "eval:doc.filter_based_on == 'Posting Date'",
		},
		{
			fieldname: "posting_end_date",
			label: __("To Posting Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.get_today(),
			depends_on: "eval:doc.filter_based_on == 'Posting Date'",
		},
		{
			fieldname: "reference_start_date",
			label: __("From Reference Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.add_months(frappe.datetime.get_today(), -2),
			depends_on: "eval:doc.filter_based_on == 'Reference Date'",
		},
		{
			fieldname: "reference_end_date",
			label: __("To Reference Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.get_today(),
			depends_on: "eval:doc.filter_based_on == 'Reference Date'",
		},
		{
			fieldname: "reference_no",
			label: __("Reference No"),
			fieldtype: "Data"
		},
		{
			fieldname: "cheque_status",
			label: __("Cheque Status"),
			fieldtype: "Select",
			options: [
				"",
				"For Collection" ,
				"Collected" ,
				"Returned" ,
				"Return To Holder" , 
				"Deposit Under Collection" , 
				"Endorsed" ,
				"Rejected" , 
				"Cancelled" ,  
				"Encashment",
				"Issuance" ,
				"Issuance From Endorsed"
			]
			// remove "Return To Customer" , "Deposited"
		},
		{
			fieldname: "bank_name" ,
			label: __("Bank Name"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Bank", txt, {
					
				});
			},
		},

		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Link",
			options: "DocType"	,
			get_query: () => {
				return {
					filters : {
						name : ["in", ["Customer", "Supplier"]]
					}
				}
			}
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
			// options: "party_type"	,
			depends_on : "party_type",
			get_data: function (txt) {
				doc = frappe.query_report.get_filter_value("party_type");
				return frappe.db.get_link_options(doc, txt, {
					// company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "names",
			label: __("Vourcher No"),
			fieldtype: "MultiSelectList",
			options: "Payment Entry" ,
			get_data: function (txt) {
				return frappe.db.get_link_options("Payment Entry", txt, {
					"cheque_status" : ["in" , [
						"For Collection" ,
						"Collected" ,
						"Returned" ,
						"Return To Holder" , 
						"Deposit Under Collection" , 
						"Endorsed" ,
						"Rejected" , 
						"Cancelled" ,  
						"Encashment",
						"Issuance" ,
						"Issuance From Endorsed"
					]]
				})
			}
		}


	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// if (column.fieldname == "cheque_status" && data )  {
		// 	if (["Return To Customer","Cancelled","Returned" , "Return To Holder" , "Rejected"].includes(data.cheque_status )) {
		// 		value = "<span style='color:red'>" + value + "</span>";
		// 	} else if (data.cheque_status == "Collected") {
		// 		value = "<span style='color:green'>" + value + "</span>";
		// 	} else if (data.cheque_status == "For Collection") {
		// 		value = "<span style='color:#2e4052'>" + value + "</span>";
		// 	} else if (['Deposited' , 'Encashment'].includes(data.cheque_status)) {
		// 		value = "<span style='color:orange'>" + value + "</span>";
		// 	} else if (data.cheque_status == "Deposit Under Collection") {
		// 		value = "<span style='color:#9F2B68'>" + value + "</span>";
		// 	} else if (data.cheque_status == "Issuance") {
		// 		value = "<span style='color:darkgrey'>" + value + "</span>";
		// 	} 
		// }

		return value;
	},
};
