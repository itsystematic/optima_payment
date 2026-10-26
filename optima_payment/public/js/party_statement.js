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
				value = optima_payment.party_statement.format_balance(data);
			} else if (column.fieldname === "voucher_type") {
				value = default_formatter(__(value), row, column, data);
			} else if (["debit", "credit"].includes(column.fieldname) && !flt(value)) {
				value = "";
			} else {
				value = default_formatter(value, row, column, data);
			}

			return data.bold ? `<b>${value}</b>` : value;
		},

		after_datatable_render(datatable) {
			optima_payment.party_statement.fit_columns(datatable);
		},

		onload(report) {
			optima_payment.party_statement.keep_columns_fitted(report);

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

// Frappe draws report columns at exactly their widths, which leaves the statement short of the
// page. They grow in proportion to fill it but never shrink below those widths, so a narrow screen
// scrolls sideways rather than cutting an amount off. Each cell's 1px border is outside its width.
optima_payment.party_statement.fit_columns = function (datatable) {
	const [row_number, ...columns] = datatable.getColumns();
	columns.forEach((column) => (column.declared_width ??= column.width));

	const borders = columns.length + 1;
	const available = datatable.datatableWrapper.clientWidth - row_number.width - borders;
	const declared = columns.reduce((sum, column) => sum + column.declared_width, 0);
	const scale = Math.max(1, available / declared);
	columns.forEach((column) => (column.width = Math.floor(column.declared_width * scale)));
	datatable.setDimensions();
};

// Refits whenever the page width may have changed, including while the user was on another page.
// frappe-datatable's fluid layout refits by itself, but a window resize while the report is hidden
// breaks its widths. Every report shares one query report page, so these handlers outlive the
// statement and check that it is the report on screen.
optima_payment.party_statement.keep_columns_fitted = function (report) {
	const statements = Object.values(optima_payment.party_statement.reports);
	const fit = () => {
		const on_screen = statements.includes(report.report_name) && report.$report.is(":visible");
		if (on_screen && report.datatable) {
			optima_payment.party_statement.fit_columns(report.datatable);
		}
	};

	$(document.body)
		.off("toggleFullWidth.party_statement")
		.on("toggleFullWidth.party_statement", fit);
	$(window)
		.off("resize.party_statement")
		.on("resize.party_statement", frappe.utils.debounce(fit, 300));
	$(report.parent).off("show.party_statement").on("show.party_statement", fit);
};

// "300.00 DR", "50.00 CR" or "0.00", formatted like the report's other numbers, in the shade of the
// row's indicator.
optima_payment.party_statement.format_balance = function (data) {
	const balance = flt(data.balance);
	const amount = frappe.format(
		Math.abs(balance),
		{ fieldtype: "Float" },
		{ always_show_decimals: true, inline: true }
	);
	const side = balance > 0 ? "DR" : balance < 0 ? "CR" : null;
	const text = side ? `${amount} ${__(side, null, "Party Statement")}` : amount;
	return `<span style="color: var(--${data.indicator.toLowerCase()}-500)">${text}</span>`;
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
