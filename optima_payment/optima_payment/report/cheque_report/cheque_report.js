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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.add_months(frappe.datetime.get_today(), -2)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default : frappe.datetime.get_today()
		},
		{
			fieldname: "reference_no",
			label: __("Cheque No"),
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
				"Return To Customer" ,
				"Return To Holder" , 
				"Deposit Under Collection" , 
				"Endorsed" ,
				"Rejected" , 
				"Cancelled" , 
				"Deposited" , 
				"Encashment",
				"Issuance" ,
				"Issuance From Endorsed"
			]
		},
		{
			fieldname: "bank_name" ,
			label: __("Bank Name"),
			fieldtype: "Link",
			options: "Bank"
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
			fieldtype: "Dynamic Link",
			options: "party_type"	,
			depends_on : "party_type"
		},


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
