frappe.provide("optima_payment");

const LEGACY_PAYMENT_ENTRY_FIELDS = [
    "custom_multi_expense",
    "custom_company_expenses",
    "custom_company_expense",
    "custom_total_amount",
];

const OPTIMA_PAYMENT_TOGGLE_FIELDS = ["is_endorsed_cheque", "multi_expense"];

const set_company_expense_totals = (frm) => {
    let total = 0;
    (frm.doc.company_expense || []).forEach((row) => {
        total += Number(row.amount || 0);
    });
    frm.set_value({ paid_amount: total, received_amount: total, total_amount: total });
    refresh_field(["total_amount", "paid_amount", "received_amount"]);
};

const set_company_expense_cost_center = (frm, cdt, cdn) => {
    const row = frappe.get_doc(cdt, cdn);
    const companyExpenseRows = frm.doc.company_expense || [];

    if (companyExpenseRows.length < 2) {
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Company",
                filters: { name: frm.doc.company },
                fieldname: "cost_center",
            },
            callback: (r) => {
                if (r.message) {
                    frappe.model.set_value(row.doctype, row.name, "cost_center", r.message.cost_center);
                }
            },
        });
        return;
    }

    if (row.parentfield) {
        frm.script_manager.copy_from_first_row(row.parentfield, row, ["cost_center"]);
    }
};

const hide_legacy_cheque_fields = (frm) => {
    LEGACY_PAYMENT_ENTRY_FIELDS.forEach((fieldname) => {
        if (frm.meta?.fields?.some((field) => field.fieldname === fieldname)) {
            frm.set_df_property(fieldname, "hidden", 1);
        }
    });
};

const set_optima_payment_fields_hidden = (frm, hidden) => {
    OPTIMA_PAYMENT_TOGGLE_FIELDS.forEach((fieldname) => {
        if (frm.fields_dict?.[fieldname]) {
            frm.set_df_property(fieldname, "hidden", hidden ? 1 : 0);
        }
    });
};

const set_dynamic_labels_safely = (frm) => {
    var company_currency = frm.doc.company
        ? frappe.get_doc(":Company", frm.doc.company)?.default_currency
        : "";

    frm.set_currency_labels(
        [
            "base_paid_amount",
            "base_received_amount",
            "base_total_allocated_amount",
            "difference_amount",
            "base_paid_amount_after_tax",
            "base_received_amount_after_tax",
            "base_total_taxes_and_charges",
        ],
        company_currency
    );

    frm.set_currency_labels(["paid_amount"], frm.doc.paid_from_account_currency);
    frm.set_currency_labels(["received_amount"], frm.doc.paid_to_account_currency);

    var party_account_currency =
        frm.doc.payment_type == "Receive"
            ? frm.doc.paid_from_account_currency
            : frm.doc.paid_to_account_currency;

    frm.set_currency_labels(
        ["total_allocated_amount", "unallocated_amount", "total_taxes_and_charges"],
        party_account_currency
    );

    var currency_field =
        frm.doc.payment_type == "Receive" ? "paid_from_account_currency" : "paid_to_account_currency";
    frm.set_df_property("total_allocated_amount", "options", currency_field);
    frm.set_df_property("unallocated_amount", "options", currency_field);
    frm.set_df_property("total_taxes_and_charges", "options", currency_field);
    frm.set_df_property("party_balance", "options", currency_field);

    frm.set_currency_labels(
        ["total_amount", "outstanding_amount", "allocated_amount"],
        party_account_currency,
        "references"
    );

    frm.set_df_property(
        "source_exchange_rate",
        "description",
        "1 " + frm.doc.paid_from_account_currency + " = [?] " + company_currency
    );

    frm.set_df_property(
        "target_exchange_rate",
        "description",
        "1 " + frm.doc.paid_to_account_currency + " = [?] " + company_currency
    );

    frm.refresh_fields();

    const party_currency =
        frm.doc.payment_type === "Receive" ? "paid_from_account_currency" : "paid_to_account_currency";
    const reference_field = frm.fields_dict["references"];
    const reference_grid = reference_field && reference_field.grid;

    if (!reference_grid) {
        console.warn("Payment Entry references grid is unavailable during set_dynamic_labels");
        return;
    }

    ["total_amount", "outstanding_amount", "allocated_amount"].forEach((fieldname) => {
        reference_grid.update_docfield_property(fieldname, "options", party_currency);
    });

    reference_grid.refresh();
};

const ensure_optima_payment_controller = (frm) => {
    if (!frm.__optima_payment_controller) {
        frm.__optima_payment_controller = new optima_payment.PaymentEntryController({ frm });
        extend_cscript(frm.cscript, frm.__optima_payment_controller);
    }

    return frm.__optima_payment_controller;
};

optima_payment.PaymentEntryController = class PaymentEntryController extends (
    frappe.ui.form.Controller
) {
    constructor(opts) {
        super(opts);
        this.mode_of_payment_doc = {};
    }
    refresh() {
        this.add_cheques_buttons() ;
        this.setup_query_filters() ;
    }

    handle_fields() {
        let me = this;
        let fieldnames_to_be_altered = {
            "is_endorsed_cheque": {
                hidden:
                    me.frm.doc.payment_type == "Receive" ||
                    (me.frm.doc.payment_type == "Pay" &&
                        me.frm.doc.mode_of_payment &&
                        me.mode_of_payment_doc.type != "Cheque") ||
                    me.mode_of_payment_doc.is_receivable_cheque == 1 ||
                    me.frm.doc.multi_expense == 1,
            },
            "multi_expense": {
                hidden: me.frm.doc.is_endorsed_cheque == 1,
            },
            "payee_name": {
                read_only: me.frm.doc.is_endorsed_cheque ,
                hidden: me.mode_of_payment_doc.type != "Cheque" ,
                reqd: me.mode_of_payment_doc.type == "Cheque" ,
            },
            "bank_name": {
                read_only: me.frm.doc.is_endorsed_cheque ,
                hidden: me.mode_of_payment_doc.type !== "Cheque" ,
                reqd: me.mode_of_payment_doc.type == "Cheque",
            },
            "paid_to": { reqd: !me.frm.doc.multi_expense },
            "paid_amount": {
                reqd: !me.frm.doc.multi_expense,
                read_only: me.frm.doc.is_endorsed_cheque,
            },
            "received_amount": {
                reqd: !me.frm.doc.multi_expense,
                read_only: me.frm.doc.is_endorsed_cheque,
            },
            "base_received_amount": { reqd: !me.frm.doc.multi_expense },
            "paid_to_account_currency": { reqd: !me.frm.doc.multi_expense },
            "total_taxes_and_charges": { hidden: me.frm.doc.multi_expense },
            "party_type": {
                hidden: me.frm.doc.multi_expense && me.frm.doc.is_endorsed_cheque == 0,
                reqd: me.frm.doc.is_endorsed_cheque ? 1 : 0,
            },
            "company_expenses": { hidden: !me.frm.doc.multi_expense },
            "party": { reqd: me.frm.doc.is_endorsed_cheque ? 1 : 0 },
            "reference_date": { read_only: me.frm.doc.is_endorsed_cheque },
            "reference_no": { read_only: me.frm.doc.is_endorsed_cheque },
            "paid_from" : { read_only : me.frm.doc.is_endorsed_cheque ? 1 :0 }
        };

        me.update_property_values(fieldnames_to_be_altered);
    }

    update_property_values(fieldnames_to_be_altered) {
        Object.keys(fieldnames_to_be_altered).forEach((fieldname) => {
            let property_to_be_altered = fieldnames_to_be_altered[fieldname];
            Object.keys(property_to_be_altered).forEach((property) => {
                let value = property_to_be_altered[property];
                this.frm.set_df_property(fieldname, property, value);
            });
        });
    }

    set_dynamic_labels(frm) {
        set_dynamic_labels_safely(frm);
    }

    receivable_cheque() {
        let me = this;
        if (this.frm.doc.receivable_cheque) {
            frappe.call({
                method: "optima_payment.cheque.api.get_receivable_cheque",
                args: {
                    name: me.frm.doc.receivable_cheque,
                },
                callback: (r) => {
                    if (r.message) {
                        me.frm.set_value(r.message[0]);
                    }
                },
            });
        }
    }

    mode_of_payment() {
        let me = this;
        frappe.run_serially([
            () => me.get_mode_of_payment_options(),
            () => me.handle_fields(),
            () => me.add_default_payee_name(),
        ]);
    }

    party() {
        this.add_default_payee_name();
    }

    payment_type() {
        this.handle_fields();
        this.add_default_payee_name();

        if (this.frm.doc.payment_type == "Receive") {
            this.frm.set_value({
                multi_expense: 0,
                receivable_cheque: "",
                is_endorsed_cheque: 0,
            });
            this.multi_expense();
        }
    }

    // Setup Filters

    setup_query_filters() {
        // Case One In multi Expense
        this.frm.set_query("mode_of_payment", (doc) => {
            let custom_filters =
                doc.payment_type === "Receive"
                    ? { is_payable_cheque: 0 }
                    : { is_receivable_cheque: 0 };
            if (
                (doc.multi_expense == 1 && doc.payment_type === "Pay") ||
                doc.payment_type === "Internal Transfer"
            ) {
                custom_filters = { is_payable_cheque: 0, is_receivable_cheque: 0 };
            }
            return {
                filters: custom_filters,
            };
        });

        // In Endoresed Cheque
        this.frm.set_query("receivable_cheque", function (doc) {
            return {
                filters: {
                    docstatus: 1,
                    payment_type: "Receive",
                    cheque_status: "For Collection",
                    paid_to_account_currency: doc.paid_from_account_currency,
                },
            };
        });

        // In Default Account In Table Multi Expense
        this.frm.set_query(
            "default_account",
            "company_expense",
            function (doc, cdt, cdn) {
                return {
                    query: "optima_payment.api.get_or_filtered_accounts",
                    filters: {
                        disabled: 0,
                        is_group: 0,
                        company: doc.company,
                    },
                };
            }
        );

        // In Party Type In Table Multi Expense
        this.frm.set_query(
            "party_type",
            "company_expense",
            function (doc, cdt, cdn) {
                return {
                    filters: {
                        name: ["in", ["Supplier", "Shareholder", "Employee"]],
                    },
                };
            }
        );
    }

    add_default_payee_name() {
        if (!this.frm.doc.mode_of_payment || this.frm.doc.is_endorsed_cheque == 1)
            return;

        if (this.mode_of_payment_doc.type == "Cheque") {
            this.frm.set_value(
                "payee_name",
                this.frm.doc.payment_type == "Pay"
                    ? this.frm.doc.party_name
                    : this.frm.doc.company
            );
        }
    }

    // Adding Buttons
    add_cheques_buttons() {
        let me = this;
        frappe.run_serially([
            () => me.get_mode_of_payment_options(),
            () => me.add_cheque_payable_buttons(),
            () => me.add_cheque_receivable_buttons(),
            () => me.handle_fields(),
        ]);
    }
    // ====== END OF INITIALIZAION ======

    // ===Methods===

    is_endorsed_cheque(doc) {
        this.handle_fields();

        if (!doc.is_endorsed_cheque) {
            this.frm.set_value("receivable_cheque", "");
        }
    }

    async get_mode_of_payment_options() {
        if (this.frm.doc.mode_of_payment) {
            this.mode_of_payment_doc = await frappe.db.get_doc(
                "Mode of Payment",
                this.frm.doc.mode_of_payment
            );
        } else {
            this.mode_of_payment_doc = {};
        }
    }

    async get_bank_fees_amount(fieldname, mode_of_payment) {
        let bank_fees_amount = 0.0;
        bank_fees_amount = await frappe.db
            .get_value("Mode of Payment", mode_of_payment, fieldname)
            .then((r) => {
                return r.message[fieldname];
            });
        return bank_fees_amount;
    }

    add_cheque_payable_buttons() {
        let me = this;
        if (
            me.mode_of_payment_doc.type == "Cheque" &&
            me.mode_of_payment_doc.is_payable_cheque == 1 &&
            me.frm.doc.payment_type == "Pay" &&
            me.frm.doc.docstatus == 1 &&
            !me.frm.doc.is_endorsed_cheque &&
            me.frm.doc.cheque_status == "Issuance" &&
            frappe.datetime.get_today() >= me.frm.doc.reference_date
        ) {
            me.frm
                .add_custom_button(__("Pay Cheque"), () => {
                    me.pay_cheque_dialog();
                })
                .removeClass("btn-default")
                .addClass("btn-success");
        }
    }

    //  RECIEVE SECTION

    add_cheque_receivable_buttons() {
        let me = this;
        if (
            me.mode_of_payment_doc.type == "Cheque" &&
            me.mode_of_payment_doc.is_receivable_cheque == 1 &&
            me.frm.doc.payment_type == "Receive" &&
            me.frm.doc.docstatus == 1
        ) {
            me.add_deposit_under_collection_button();
            me.add_collect_cheque_button();
            me.add_return_cheque_button();
            me.add_reject_cheque_button();
            me.add_reject_redeposit_and_return_to_holder_button();
        }
    }

    add_deposit_under_collection_button() {
        let me = this;
        if (me.frm.doc.cheque_status == "For Collection") {
            me.frm
                .add_custom_button(__("Deposit Under Collection"), () => {
                    me.create_frappe_prompt(
                        [],
                        "optima_payment.cheque.api.deposit_under_collection",
                        __("Deposit Under Collection"),
                        __("Deposit")
                    );
                })
                .removeClass("btn-default")
                .addClass("btn-success");
        }
    }

    add_collect_cheque_button() {
        let me = this;
        if (
            ["Deposit Under Collection", "Deposited"].includes(
                me.frm.doc.cheque_status
            )
        ) {
            me.frm
                .add_custom_button(__("Collect"), () => {
                    me.collect_cheque_dialog();
                })
                .removeClass("btn-default")
                .addClass("btn-success");
        }
    }

    add_return_cheque_button() {
        if (
            ["Deposit Under Collection", "Deposited"].includes(
                this.frm.doc.cheque_status
            )
        ) {
            this.frm
                .add_custom_button(__("Return"), () => {
                    let fields = [
                        {
                            label: __("Remarks"),
                            fieldname: "remarks",
                            fieldtype: "Data",
                            reqd: 1,
                            default: "شيك مرتد",
                        },
                    ];

                    this.create_frappe_prompt(
                        fields,
                        "optima_payment.cheque.api.return_cheque",
                        __("Return Cheque"),
                        __("Return")
                    );
                })
                .removeClass("btn-default")
                .addClass("btn-warning");
        }
    }

    async add_reject_cheque_button() {
        let me = this;
        if (
            ["Deposit Under Collection", "Deposited"].includes(
                this.frm.doc.cheque_status
            )
        ) {
            this.frm
                .add_custom_button(__("Reject"), async () => {
                    let fields = await this.get_dialog_fields_return_reject();
                    // console.log(fields[fields.length-1].label, fields[fields.length-1].fieldname);
                    fields[fields.length - 1].default = "شيك مرفوض";
                    this.create_frappe_prompt(
                        fields,
                        "optima_payment.cheque.api.reject_cheque",
                        __("Reject Cheque"),
                        __("Reject")
                    );
                    if (this.frm.doc.cheque_deposit_slip) {
                        this.frm.doc.cheque_deposit_slip == "";
                    }
                })
                .removeClass("btn-default")
                .addClass("btn-danger");
        }
    }

    add_reject_redeposit_and_return_to_holder_button() {
        let me = this;
        if (me.frm.doc.cheque_status === "Rejected") {
            me.frm
                .add_custom_button(__("Redeposit"), () => {
                    frappe.call({
                        method: "optima_payment.cheque.api.redeposit_cheque",
                        args: {
                            docname: me.frm.doc.name,
                        },
                        callback: () => {
                            me.frm.reload_doc();
                        },
                    });
                })
                .removeClass("btn-default")
                .addClass("btn-success");
            me.frm
                .add_custom_button(__("Return To Holder"), () => {
                    me.create_frappe_prompt(
                        [
                            {
                                label: __("Remarks"),
                                fieldname: "remarks",
                                fieldtype: "Data",
                                reqd: 1,
                                default: "شيك مرفوض",
                            },
                        ],
                        "optima_payment.cheque.api.return_to_holder",
                        __("Return To Holder"),
                        __("Return To Holder")
                    );
                })
                .removeClass("btn-default")
                .addClass("btn-danger");
        }
    }
    // ====== END OF METHODS ======

    // ===DIALOGS===

    pay_cheque_dialog() {
        let fields = [
            { fieldtype: "Column Break" },
            {
                label: "Mode of Payment",
                fieldname: "mode_of_payment",
                fieldtype: "Link",
                options: "Mode of Payment",
                reqd: 1,
                get_query: () => {
                    return {
                        query: "optima_payment.cheque.api.get_mode_of_payment",
                        filters: {
                            company: this.frm.doc.company,
                            default_currency: this.get_default_currency(),
                            type: "Bank",
                        },
                    };
                },
            },
        ];
        this.create_frappe_prompt(
            fields,
            "optima_payment.cheque.api.pay_cheque",
            __("Pay Cheque"),
            __("Pay")
        );
    }

    async collect_cheque_dialog() {
        let me = this;
        let default_cost_center = me.get_default_cost_center();

        let fields = [
            {
                label: __("Has Bank Commissions"),
                fieldname: "has_bank_commissions",
                fieldtype: "Check",
            },
            { fieldtype: "Column Break" },
            {
                label: __("Mode of Payment"),
                fieldname: "mode_of_payment",
                fieldtype: "Link",
                options: "Mode of Payment",
                reqd: 1,
                // depends_on: 'eval: doc.has_bank_fees == 1' , mandatory_depends_on: 'eval: doc.has_bank_fees == 1 ;',
                get_query: () => {
                    return {
                        query: "optima_payment.cheque.api.get_mode_of_payment",
                        filters: {
                            company: me.frm.doc.company,
                            default_currency: me.get_default_currency(),
                            type: ["in", ["Bank", "Cash"]],
                        },
                    };
                },
                onchange: async () => {
                    let mode_of_payment = cur_dialog.get_value("mode_of_payment");
                    let bank_fees_amount = await me.get_bank_fees_amount(
                        "cheque_collection_fee",
                        mode_of_payment
                    );
                    cur_dialog.set_value("bank_fees_commission", bank_fees_amount);
                    // cur_dialog.refresh();
                },
            },
            {
                label: __("Bank Fees Commission"),
                fieldname: "bank_fees_commission",
                fieldtype: "Currency",
                default: 0.0,
                // read_only: 1,
                depends_on: "eval: doc.has_bank_commissions == 1 ;",
                mandatory_depends_on: "eval: doc.has_bank_commissions == 1 ;",
            },
            {
                label: __("Cost Center"),
                fieldname: "cost_center",
                options: "Cost Center",
                fieldtype: "Link",
                default: default_cost_center,
                // read_only: 1,
                depends_on: "eval: doc.has_bank_commissions == 1 ;",
                mandatory_depends_on: "eval: doc.has_bank_commissions == 1 ;",
                get_query: () => {
                    return {
                        filters: {
                            company: me.frm.doc.company,
                            is_group: 0,
                        },
                    };
                },
            },
        ];

        this.create_frappe_prompt(
            fields,
            "optima_payment.cheque.api.collect_cheque",
            __("Collect Cheque"),
            __("Collect")
        );
    }

    async get_dialog_fields_return_reject() {
        let me = this;
        let default_cost_center = me.get_default_cost_center();
        return [
            {
                label: __("Has Bank Fees"),
                fieldname: "has_bank_fees",
                fieldtype: "Check",
            },
            {
                fieldtype: "Column Break",
            },
            {
                label: __("Mode of Payment"),
                fieldname: "mode_of_payment",
                fieldtype: "Link",
                options: "Mode of Payment",
                depends_on: "eval: doc.has_bank_fees == 1 ;",
                mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
                get_query: () => {
                    return {
                        query: "optima_payment.cheque.api.get_mode_of_payment",
                        filters: {
                            company: me.frm.doc.company,
                            default_currency: me.get_default_currency(),
                            type: "Bank",
                        },
                    };
                },
                onchange: async () => {
                    let mode_of_payment = cur_dialog.get_value("mode_of_payment");
                    let bank_fees_amount = await me.get_bank_fees_amount(
                        "cheque_rejection_fee",
                        mode_of_payment
                    );
                    cur_dialog.set_value("bank_fees_amount", bank_fees_amount);
                },
            },
            {
                label: __("Bank Fees Amount"),
                fieldname: "bank_fees_amount",
                fieldtype: "Currency",
                default: 0.0,
                // read_only : 1,
                depends_on: "eval: doc.has_bank_fees == 1 ;",
                mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
            },
            {
                label: __("Cost Center"),
                fieldname: "cost_center",
                options: "Cost Center",
                fieldtype: "Link",
                default: default_cost_center,
                // read_only: 1,
                depends_on: "eval: doc.has_bank_fees == 1 ;",
                mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
            },
            {
                fieldtype: "Section Break",
            },
            {
                label: __("Remarks"),
                fieldname: "remarks",
                fieldtype: "Data",
                reqd: 1,
                default: " ",
            },
        ];
    }
    get_default_cost_center() {
        let company_settings =
            frappe.boot[`default_cost_center_${this.frm.doc.company}`];
        let default_currency = this.get_default_currency();
        return company_settings[default_currency];
    }

    get_default_currency() {
        return this.frm.doc.payment_type == "Receive"
            ? this.frm.doc.paid_to_account_currency
            : this.frm.doc.paid_from_account_currency;
    }

    // ====== END OF DIALOGS ======

    // ===EVENT HANDLER===

    create_frappe_prompt(fields, method, title, primary_label) {
        let me = this;
        let fd = [
            {
                label: __("Posting Date"),
                fieldname: "posting_date",
                fieldtype: "Date",
                reqd: 1,
                default: frappe.datetime.now_date(),
            },
            ...fields,
        ];
        let d = frappe.prompt(
            fd,
            (values) => {
                if (values.posting_date < me.frm.doc.posting_date) {
                    frappe.throw(
                        __("Posting Date should be greater than {0}", [
                            me.frm.doc.posting_date,
                        ])
                    );
                }
                values["docname"] = me.frm.doc.name;

                frappe.call({
                    method: method,
                    args: values,
                    callback: (r) => {
                        console.log(r);
                        console.log(fields);
                        me.frm.reload_doc();
                    },
                });
            },
            __(title),
            __(primary_label)
        );
        const primary_button = d.get_primary_btn();
        switch (primary_label) {
            case "Collect":
                primary_button.removeClass("btn-default").addClass("btn-success");
                break;
            case "Return":
                primary_button.removeClass("btn-default").addClass("btn-warning");
                break;
            case "Reject":
            case "Return To Holder":
                primary_button.removeClass("btn-default").addClass("btn-danger");
                break;
        }
    }

    // ====== END OF EVENT HANDLER ======

    //  ======  Multi Expense ======

    amount(doc, cdt, cdn) {
        set_company_expense_totals(this.frm);
    }

    // Change Mandatory
    multi_expense() {
        this.frm.set_value({ party_type: ''});
        this.handle_fields();
    }
};

frappe.ui.form.on("Payment Entry", {
    setup(frm) {
        frm.events.set_dynamic_labels = (target_frm) => {
            set_dynamic_labels_safely(target_frm || frm);
        };
        hide_legacy_cheque_fields(frm);
        set_optima_payment_fields_hidden(frm, true);
        ensure_optima_payment_controller(frm);
    },
    refresh(frm) {
        hide_legacy_cheque_fields(frm);
        if (frm.doc.company && !frm.__optima_payment_company_state_loaded) {
            frm.trigger("company");
        }
    },
    company(frm) {
        hide_legacy_cheque_fields(frm);
        frm.__optima_payment_company_state_loaded = true;

        if (!frm.doc.company) {
            frm.__optima_payment_enabled = false;
            set_optima_payment_fields_hidden(frm, true);
            return;
        }

        if (frm.doc.company) {
            frappe.call({
                method: "optima_payment.cheque.api.get_company_settings",
                args: {
                    company: frm.doc.company,
                },
                callback: (r) => {
                    if (r.message && r.message.enable_optima_payment) {
                        frm.__optima_payment_enabled = true;
                        set_optima_payment_fields_hidden(frm, false);

                        const controller = ensure_optima_payment_controller(frm);
                        frappe.run_serially([
                            () => controller.get_mode_of_payment_options(),
                            () => controller.handle_fields(),
                            () => controller.setup_query_filters(),
                            () => controller.add_default_payee_name(),
                        ]);
                    } else {
                        frm.__optima_payment_enabled = false;
                        set_optima_payment_fields_hidden(frm, true);
                    }
                },
            });
        }
    },
});

frappe.ui.form.on("Company Expense Details", {
    amount(frm) {
        set_company_expense_totals(frm);
    },
    company_expense_add(frm, cdt, cdn) {
        set_company_expense_cost_center(frm, cdt, cdn);
        set_company_expense_totals(frm);
    },
    company_expense_remove(frm) {
        set_company_expense_totals(frm);
    },
});

ensure_optima_payment_controller(cur_frm);
