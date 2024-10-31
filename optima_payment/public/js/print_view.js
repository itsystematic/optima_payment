frappe.pages["print"].on_page_load = function (wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
    });

    let print_view = new frappe.ui.form.PrintView(wrapper);

    $(wrapper).bind("show", () => {
        const route = frappe.get_route();
        const doctype = route[1];
        const docname = route.slice(2).join("/");
        if (!frappe.route_options || !frappe.route_options.frm) {
            frappe.model.with_doc(doctype, docname, () => {
                let frm = { doctype: doctype, docname: docname };
                frm.doc = frappe.get_doc(doctype, docname);
                frappe.model.with_doctype(doctype, async () => {
                    frm.meta = frappe.get_meta(route[1]);
                    await print_view.fetch_bank_print_formats(frm);
                    print_view.show(frm);
                });
            });
        } else {
            print_view.frm = frappe.route_options.frm.doctype
                ? frappe.route_options.frm
                : frappe.route_options.frm.frm;
            print_view.fetch_bank_print_formats(print_view.frm);
            frappe.route_options.frm = null;
            print_view.show(print_view.frm);
        }
    });
};


frappe.ui.form.PrintView = class PrintView extends frappe.ui.form.PrintView {
    constructor(wrapper) {
        super(wrapper);
        this.print_format_names = []
    }

    async fetch_bank_print_formats(frm) {
        try {
            const frm_mode_of_payment = frm.doc.mode_of_payment;
            const mode_of_payment = await frappe.db.get_doc("Mode of Payment", frm_mode_of_payment);
            this.type = mode_of_payment.type;
            if (this.type !== "Cheque") {
                this.type = "";
                return;
            };
            const bank_name = frm.doc.bank_name; // Get the bank name from the form
            const bank = await frappe.db.get_doc("Bank", bank_name); // Await fetching the bank document
            this.print_format_names = bank.bank_print_format.map(row => row.print_format); // Extract print formats
        } catch (error) {
            console.log(error); // Show error message if something goes wrong
        }
    }



    setup_sidebar() {
        this.sidebar = this.page.sidebar.addClass("print-preview-sidebar");

        this.print_format_selector = this.add_sidebar_item({
            fieldtype: "Link",
            fieldname: "print_format",
            options: "Print Format",
            label: __("Print Format"),
            get_query: () => {
                if (this.frm.doc.mode_of_payment.includes("Cheque")) {
                    return {
                        filters: { doc_type: this.frm.doctype, name: ["in", this.print_format_names] }

                    };
                }
                return { filters: { doc_type: this.frm.doctype, name: ["NOT LIKE", "SA-%"] } };
            },
            change: () => this.refresh_print_format(),
        }).$input;

        this.language_selector = this.add_sidebar_item({
            fieldtype: "Link",
            fieldname: "language",
            label: __("Language"),
            options: "Language",
            change: () => {
                this.set_user_lang();
                this.preview();
            },
        }).$input;

        let description = "";
        if (!cint(this.print_settings.repeat_header_footer)) {
            description =
                "<div class='form-message yellow p-3 mt-3'>" +
                __("Footer might not be visible as {0} option is disabled</div>", [
                    `<a href="/app/print-settings/Print Settings">${__(
                        "Repeat Header and Footer"
                    )}</a>`,
                ]);
        }
        const print_view = this;
        this.letterhead_selector = this.add_sidebar_item({
            fieldtype: "Link",
            fieldname: "letterhead",
            options: "Letter Head",
            label: __("Letter Head"),
            description: description,
            change: function () {
                this.set_description(this.get_value() ? description : "");
                print_view.preview();
            },
        }).$input;
        this.sidebar_dynamic_section = $(`<div class="dynamic-settings"></div>`).appendTo(
            this.sidebar
        );
    }
    set_default_print_format() {
        if (this.frm.doc.doctype === "Payment Entry") {
            if (this.frm.doc.mode_of_payment.includes("Cheque")) {
                console.log('Cheque');
                this.print_format_selector.empty(this.print_format_names.length > 0 ? this.print_format_names[0] : this.frm.meta.default_print_format);
            }
            else {
                console.log('Not Cheque');
                this.print_format_selector.empty();
                this.print_format_selector.val(this.frm.meta.default_print_format);
            }
        } else {
            this.print_format_selector.empty();
            this.print_format_selector.val(this.frm.meta.default_print_format);
        }
    }
};