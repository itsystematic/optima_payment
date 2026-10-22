// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

frappe.provide("optima_payment.party_statement");

frappe.pages["party-statement"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Statement of Account"),
		single_column: true,
	});
	wrapper.statement_preview = new optima_payment.party_statement.Preview(page);
};

frappe.pages["party-statement"].on_page_show = function (wrapper) {
	wrapper.statement_preview.apply_route_options();
};

// The statement exactly as the PDF and the email attachment show it: the server renders one HTML page
// for all three, and the iframe keeps the desk's CSS out of it.
optima_payment.party_statement.Preview = class {
	constructor(page) {
		this.page = page;
		this.method = "optima_payment.party_statement.api";
		this.fieldnames = ["party_type", "party", "company", "from_date", "to_date"];
		this.refresh = frappe.utils.debounce(() => this.render(), 300);

		this.make_fields();
		this.make_actions();
		this.make_body();
	}

	make_fields() {
		this.page.add_field({
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Select",
			options: Object.keys(optima_payment.party_statement.reports),
			default: "Customer",
			change: async () => {
				await this.field("party").set_value("");
				this.refresh();
			},
		});
		this.page.add_field({
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			get_options: () => this.field("party_type").get_value(),
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			change: () => this.refresh(),
		});
	}

	make_actions() {
		this.page.set_primary_action(__("Send Email"), () => this.send_email(), "mail");
		this.page.add_button(__("Download PDF"), () => this.download("download_pdf"), {
			icon: "small-file",
		});
		this.page.add_button(__("Print"), () => this.print(), { icon: "printer" });
		this.page.add_button(__("Export to Excel"), () => this.download("download_excel"), {
			icon: "file",
		});
		this.page.add_button(__("Open Report"), () => this.open_report(), { icon: "list" });
	}

	make_body() {
		this.$message = $(`<div class="party-statement-message text-muted"></div>`);
		this.$frame = $(`<iframe class="party-statement-frame hidden" frameborder="0"></iframe>`);
		this.frame = this.$frame.get(0);
		// The statement's height is known only once it is laid out; the frame grows to it so the page
		// scrolls instead of the frame.
		this.frame.addEventListener("load", () => {
			this.frame.style.height = `${this.frame.contentDocument.documentElement.scrollHeight}px`;
		});
		$(this.page.body).addClass("party-statement-page").append(this.$message, this.$frame);
	}

	field(fieldname) {
		return this.page.fields_dict[fieldname];
	}

	async apply_route_options() {
		const options = frappe.route_options;
		frappe.route_options = null;

		// party_type first: changing it clears the party.
		for (const fieldname of this.fieldnames) {
			if (options && options[fieldname]) {
				await this.field(fieldname).set_value(options[fieldname]);
			}
		}
		this.refresh();
	}

	get_args() {
		const args = {};
		for (const fieldname of this.fieldnames) {
			// The value the control last accepted. get_value() reads the input's text, which while the
			// user is still typing a party is not yet a valid name.
			args[fieldname] = this.field(fieldname).value;
		}
		return Object.values(args).every(Boolean) ? args : null;
	}

	require_args() {
		const args = this.get_args();
		if (!args) {
			frappe.throw(__("Select a party, a company and a period first."));
		}
		return args;
	}

	render() {
		const args = this.get_args();
		if (!args) {
			this.show_message(__("Select a party, a company and a period to see the statement."));
			return;
		}

		// A slower earlier request must not overwrite a newer statement.
		const request = (this.request = {});
		frappe.call({ method: `${this.method}.get_preview_html`, args }).then((r) => {
			if (request !== this.request) {
				return;
			}
			this.$message.addClass("hidden");
			this.$frame.removeClass("hidden");
			this.frame.srcdoc = r.message;
		});
	}

	show_message(message) {
		this.request = null;
		this.$frame.addClass("hidden").removeAttr("srcdoc");
		this.$message.text(message).removeClass("hidden");
	}

	print() {
		this.require_args();
		this.frame.contentWindow.print();
	}

	download(method) {
		const args = this.require_args();
		window.open(
			frappe.urllib.get_full_url(
				`/api/method/${this.method}.${method}?${new URLSearchParams(args).toString()}`
			)
		);
	}

	open_report() {
		const { party_type, ...filters } = this.require_args();
		frappe.set_route("query-report", optima_payment.party_statement.reports[party_type], filters);
	}

	async send_email() {
		const args = this.require_args();
		const { message } = await frappe.call({
			method: `${this.method}.make_email_attachment`,
			args,
			freeze: true,
			freeze_message: __("Preparing the statement PDF..."),
		});

		// Linking the email to the party puts it on the party's timeline.
		const composer = new frappe.views.CommunicationComposer({
			doc: { doctype: args.party_type, name: args.party },
			recipients: message.recipients,
			subject: message.subject,
		});
		composer.render_attachment_rows(message.file);
	}
};
