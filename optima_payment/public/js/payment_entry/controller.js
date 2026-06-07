frappe.provide("optima_payment");

optima_payment.PaymentEntryController = class PaymentEntryController extends (
    frappe.ui.form.Controller
) {
    constructor(opts) {
        super(opts);
        this.mode_of_payment_doc = {};
        this.dialogFactory = new optima_payment.DialogFactory(opts.frm);
        this.fieldManager = new optima_payment.FieldVisibilityManager(opts.frm);
        this.queryFilterManager = new optima_payment.QueryFilterManager(opts.frm);
        this.buttonManager = new optima_payment.ButtonManager(
            opts.frm,
            this.dialogFactory,
            this.create_frappe_prompt.bind(this)
        );
    }

    // ================================================================================================
    // FORM LIFECYCLE
    // ================================================================================================

    refresh() {
        frappe.run_serially([
            () => this.get_mode_of_payment_options(),
            () => this.buttonManager.addAll(this.mode_of_payment_doc),
            () => this.fieldManager.updateAll(this.mode_of_payment_doc),
            () => this.queryFilterManager.setup(),
        ]);
    }

    set_dynamic_labels(frm) {
        set_dynamic_labels_safely(frm);
    }

    // ================================================================================================
    // FIELD EVENTS
    // ================================================================================================

    receivable_cheque() {
        if (!this.frm.doc.receivable_cheque) {
            return;
        }

        frappe.call({
            method: "optima_payment.cheque.api.get_receivable_cheque",
            args: {
                name: this.frm.doc.receivable_cheque,
            },
            callback: (r) => {
                if (r.message) {
                    this.frm.set_value(r.message[0]);
                }
            },
        });
    }

    mode_of_payment() {
        frappe.run_serially([
            () => this.get_mode_of_payment_options(),
            () => this.sync_mode_of_payment_bank_fees(),
            () => this.fieldManager.updateAll(this.mode_of_payment_doc),
            () => this.add_default_payee_name(),
        ]);
    }

    party() {
        this.add_default_payee_name();
    }

    payment_type() {
        this.fieldManager.updateAll(this.mode_of_payment_doc);
        this.add_default_payee_name();

        if (this.frm.doc.payment_type == optima_payment.config.PAYMENT_TYPES.RECEIVE) {
            this.frm.set_value({
                multi_expense: 0,
                receivable_cheque: "",
                is_endorsed_cheque: 0,
            });
            this.multi_expense();
        }
    }

    is_endorsed_cheque(doc) {
        this.fieldManager.updateAll(this.mode_of_payment_doc);

        if (!doc.is_endorsed_cheque) {
            this.frm.set_value("receivable_cheque", "");
        }
    }

    add_default_payee_name() {
        if (!this.frm.doc.mode_of_payment || this.frm.doc.is_endorsed_cheque == 1) {
            return;
        }

        if (this.mode_of_payment_doc.type == optima_payment.config.MODE_OF_PAYMENT_TYPES.CHEQUE) {
            this.frm.set_value(
                "payee_name",
                this.frm.doc.payment_type == optima_payment.config.PAYMENT_TYPES.PAY
                    ? this.frm.doc.party_name
                    : this.frm.doc.company
            );
        }
    }

    // ================================================================================================
    // SHARED HELPERS
    // ================================================================================================

    async get_mode_of_payment_options() {
        if (this.frm.doc.mode_of_payment) {
            this.mode_of_payment_doc = await frappe.db.get_doc(
                "Mode of Payment",
                this.frm.doc.mode_of_payment
            );
            return;
        }

        this.mode_of_payment_doc = {};
    }

    async sync_mode_of_payment_bank_fees() {
        const updates = {};
        const bankFees = this.frm.doc.mode_of_payment
            ? Number(this.mode_of_payment_doc.bank_fees ?? 0)
            : 0;

        if (this.frm.fields_dict.bank_fees) {
            updates.bank_fees = bankFees;
        }

        if (this.frm.fields_dict.pay_fees) {
            updates.pay_fees = bankFees;
        }

        if (Object.keys(updates).length) {
            await this.frm.set_value(updates);
        }
    }

    create_frappe_prompt(dialogConfig) {
        const fields = [
            {
                label: __("Posting Date"),
                fieldname: "posting_date",
                fieldtype: "Date",
                reqd: 1,
                default: frappe.datetime.now_date(),
            },
            ...(dialogConfig.fields || []),
        ];

        const dialog = frappe.prompt(
            fields,
            (values) => {
                if (values.posting_date < this.frm.doc.posting_date) {
                    frappe.throw(
                        __("Posting Date should be greater than {0}", [
                            this.frm.doc.posting_date,
                        ])
                    );
                }

                values.docname = this.frm.doc.name;
                frappe.call({
                    method: dialogConfig.method,
                    args: values,
                    callback: () => {
                        this.frm.reload_doc();
                    },
                });
            },
            __(dialogConfig.title),
            __(dialogConfig.primaryLabel)
        );

        const btnClass =
            optima_payment.config.CHEQUE_BUTTON_CLASSES[dialogConfig.primaryLabel];
        if (btnClass) {
            dialog.get_primary_btn().removeClass("btn-default").addClass(btnClass);
        }
    }

    amount(doc, cdt, cdn) {
        set_company_expense_totals(this.frm);
    }

    // ================================================================================================
    // MULTI EXPENSE LOGIC
    // ================================================================================================
    // These toggles stay coordinated so cheque-specific field states do not drift.

    multi_expense() {
        const updates = { party_type: "" };

        // Keep these toggles mutually exclusive so dependent fields stay in sync.
        if (this.frm.doc.multi_expense == 1 && this.frm.fields_dict.has_bank_fees) {
            updates.has_bank_fees = 0;
        }

        frappe.run_serially([
            () => this.frm.set_value(updates),
            () => this.fieldManager.updateAll(this.mode_of_payment_doc),
        ]);
    }

    has_bank_fees() {
        const updates = {};

        if (this.frm.doc.has_bank_fees == 1 && this.frm.doc.multi_expense == 1) {
            updates.multi_expense = 0;
        }

        if (Object.keys(updates).length) {
            frappe.run_serially([
                () => this.frm.set_value(updates),
                () => this.fieldManager.updateAll(this.mode_of_payment_doc),
            ]);
            return;
        }

        this.fieldManager.updateAll(this.mode_of_payment_doc);
    }
};

// ================================================================================================
// FORM REGISTRATION
// ================================================================================================

frappe.ui.form.on("Payment Entry", {
    setup(frm) {
        const controller = ensure_optima_payment_controller(frm);

        frm.events.set_dynamic_labels = (target_frm) => {
            set_dynamic_labels_safely(target_frm || frm);
        };
        controller.fieldManager.hideLegacyFields();
        controller.fieldManager.setOptimaFieldsHidden(true);
    },
    before_save(frm) {
        if (frm.doc.multi_expense === 1) {
            frm.doc.party_type = "";
        }
    },
    refresh(frm) {
        const controller = ensure_optima_payment_controller(frm);

        controller.fieldManager.hideLegacyFields();
        if (frm.doc.company && !frm.__optima_payment_company_state_loaded) {
            frm.trigger("company");
        }
    },
    company(frm) {
        const controller = ensure_optima_payment_controller(frm);

        controller.fieldManager.hideLegacyFields();
        frm.__optima_payment_company_state_loaded = true;

        if (!frm.doc.company) {
            frm.__optima_payment_enabled = false;
            controller.fieldManager.setOptimaFieldsHidden(true);
            return;
        }

        frappe.call({
            method: "optima_payment.cheque.api.get_company_settings",
            args: {
                company: frm.doc.company,
            },
            callback: (r) => {
                if (r.message && r.message.enable_optima_payment) {
                    frm.__optima_payment_enabled = true;
                    controller.fieldManager.setOptimaFieldsHidden(false);

                    frappe.run_serially([
                        () => controller.get_mode_of_payment_options(),
                        () => controller.fieldManager.updateAll(controller.mode_of_payment_doc),
                        () => controller.queryFilterManager.setup(),
                        () => controller.add_default_payee_name(),
                    ]);
                    return;
                }

                frm.__optima_payment_enabled = false;
                controller.fieldManager.setOptimaFieldsHidden(true);
            },
        });
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
