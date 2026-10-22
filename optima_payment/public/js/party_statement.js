frappe.provide("optima_payment.party_statement");

optima_payment.party_statement.reports = {
	Customer: "Customer Statement",
	Supplier: "Supplier Statement",
};

// Shared by the Customer Statement and Supplier Statement reports.
optima_payment.party_statement.report_settings = function (party_type) {
	return {
		filters: [
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				reqd: 1,
			},
			{
				fieldname: "party",
				label: __(party_type),
				fieldtype: "Link",
				options: party_type,
				reqd: 1,
			},
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
				reqd: 1,
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
		],

		formatter(value, row, column, data, default_formatter) {
			if (!data) {
				return default_formatter(value, row, column, data);
			}

			if (column.fieldname === "balance") {
				value = optima_payment.party_statement.format_balance(data.balance, data.currency);
			} else if (column.fieldname === "voucher_type") {
				value = default_formatter(__(value), row, column, data);
			} else if (["debit", "credit"].includes(column.fieldname) && !flt(value)) {
				value = `<div class="text-center">-</div>`;
			} else {
				value = default_formatter(value, row, column, data);
			}

			return data.bold ? `<b>${value}</b>` : value;
		},

		onload(report) {
			report.page.add_inner_button(__("Preview"), () => {
				const filters = report.get_filter_values();
				if (!filters.party) {
					frappe.throw(__("Select a {0} first.", [__(party_type)]));
				}
				frappe.route_options = { party_type, ...filters };
				frappe.set_route("party-statement");
			});
		},
	};
};

// A balance reads as its amount and side, as on the printed statement: DR in red, CR in green.
optima_payment.party_statement.format_balance = function (balance, currency) {
	const side = flt(balance) < 0 ? "CR" : "DR";
	const color = side === "DR" ? "text-danger" : "text-success";
	const amount = format_currency(Math.abs(flt(balance)), currency);
	return `<span class="${color}">${amount} ${__(side, null, "Party Statement")}</span>`;
};

optima_payment.party_statement.add_form_button = function (frm) {
	if (frm.is_new()) {
		return;
	}

	frm.add_custom_button(
		__("Statement of Account"),
		() => {
			frappe.set_route("query-report", optima_payment.party_statement.reports[frm.doctype], {
				party: frm.doc.name,
				company: frappe.defaults.get_user_default("Company"),
			});
		},
		__("View")
	);
};
