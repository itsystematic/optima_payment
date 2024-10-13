
frappe.provide("optima_payment");


optima_payment.PaymentEntryController = class PaymentEntryController extends frappe.ui.form.Controller {


    // ===INITIALIZE===
    refresh() {
        this.reset_fields_of_cheque();
        this.handle_fields_is_endorsed_cheque();
        this.handle_fields_multi_expense();
        this.add_cheques_buttons();
        this.setup_query_filters()
    }


    receivable_cheque() {
        let me = this ;
        if (this.frm.doc.receivable_cheque) {
            frappe.call({
                method : "optima_payment.cheque.api.get_receivable_cheque",
                args : {
                    name : me.frm.doc.receivable_cheque
                },
                callback:(r) => {
                    if(r.message) {
                        me.frm.set_value(r.message[0]);
                    }
                    
                }
            })
        }
    }


    mode_of_payment() {
        let me = this ;
        frappe.run_serially([
            () => me.get_mode_of_payment_options() ,
            () => me.reset_field_of_endorsed_cheque(),
            () => me.show_or_hide_multi_expense()
        ])

    }


    reset_field_of_endorsed_cheque() {
        if (this.mode_of_payment_doc.is_payable_cheque == 0) {
            const fields = ['payee_name', 'bank_name', 'reference_no', 'reference_date', 'paid_amount', "received_amount"];

            this.frm.set_value('is_endorsed_cheque', 0);
            fields.forEach(field => {
                this.frm.set_value(field, null);
                this.frm.set_df_property(field, 'read_only', 0);
            });
        }
    }

    show_or_hide_multi_expense() {
        if (this.mode_of_payment_doc.type == "Cheque") {
            this.frm.set_df_property('multi_expense', 'hidden', 1);
        }else {
            this.frm.set_df_property('multi_expense', 'hidden', 0);
        }
    }
    // Reset Fields
    reset_fields_of_cheque() {

        if (this.frm.doc.docstatus == 0 && this.frm.is_new()) {
            this.frm.set_value({
                "cheque_status": "",
                "pay_mode_of_payment": "",
                "bank_fees_amount": "",
                "receivable_cheque" : "",
                "payee_name" : "" ,
                'bank_name' : "" ,
                "is_endorsed_cheque": 0 ,
                "multi_expense" : 0 ,
            })
        }
    }

    payment_type() {
        if (this.frm.doc.payment_type == "Receive") {
            this.frm.doc.multi_expense = 0;
            this.multi_expense();
        }
    }

    // Setup Filters

    setup_query_filters() {
        // Case One In multi Expense 
        this.frm.set_query("mode_of_payment", (doc) => {
            let custom_filters = {};
            
            if ((doc.multi_expense == 1  && doc.payment_type == "Pay") || doc.payment_type == "Internal Transfer") {
                custom_filters = { "is_payable_cheque": 0, "is_receivable_cheque": 0 };
            } else if (doc.multi_expense == 0 && ["Pay" , "Receive"].includes(doc.payment_type)) {
                custom_filters = doc.payment_type === "Receive" ? { "is_payable_cheque": 0 } : { "is_receivable_cheque": 0 };
            } 

            return {
                filters: custom_filters
            }
        })

        // In Endoresed Cheque
        this.frm.set_query("receivable_cheque", function () {
            return {
                filters: {
                    "docstatus": 1,
                    "payment_type": "Receive",
                    "cheque_status": "For Collection",
                }
            };
        });

        // In Default Account In Table Multi Expense
        this.frm.set_query("default_account", "company_expense", function (doc, cdt, cdn) {
            return {
                filters: {
                    "disabled": 0,
                    "root_type": ["in", ["Expense", "Liability"]],
                    "is_group": 0,
                    "company": doc.company
                }
            };
        });

        // In Party Type In Table Multi Expense 
        this.frm.set_query("party_type", "company_expense", function (doc, cdt, cdn) {
            return {
                filters: {
                    // "name": "Party Type",
                    "name": ["in", ["Supplier", "Shareholder" , "Employee"]],
                }
			};
        });
    }

    // Adding Buttons
    add_cheques_buttons() {
        let me = this;
        frappe.run_serially([
            () => me.get_mode_of_payment_options(),
            () => me.add_cheque_payable_buttons(),
            () => me.add_cheque_receivable_buttons(),
        ])
    }
    // ====== END OF INITIALIZAION ======

    // ===Methods===

    is_endorsed_cheque(doc) {
        
        if (!doc.is_endorsed_cheque) {
            this.frm.set_value("receivable_cheque" , "");
        }
        this.handle_fields_is_endorsed_cheque();
    }

    handle_fields_is_endorsed_cheque() {
        let doc = this.frm.doc;
        if (!this.mode_of_payment_doc) {
            this.mode_of_payment_doc = {};
        }

        let fields = [
            { field: "payee_name", property: "read_only", value: doc.is_endorsed_cheque  },
            { field: "payee_name", property: "hidden", value: !["Bank" , "Cheque"].includes(this.mode_of_payment_doc.type)},
            { field: "bank_name", property: "read_only", value: doc.is_endorsed_cheque },
            { field: "bank_name", property: "hidden", value: !["Bank" , "Cheque"].includes(this.mode_of_payment_doc.type) },
            { field: "reference_no", property: "read_only", value: doc.is_endorsed_cheque },
            { field: "reference_date", property: "read_only", value: doc.is_endorsed_cheque },
            { field: "paid_amount", property: "read_only", value: doc.is_endorsed_cheque },
            { field: "received_amount", property: "read_only", value: doc.is_endorsed_cheque },
            { field: "party_type", property: "reqd", value: doc.is_endorsed_cheque  ? 1 : 0 },
            { field: "party", property: "reqd", value: doc.is_endorsed_cheque  ? 1 : 0 },
        ]

        this.update_property_values(fields);
    }


    async get_mode_of_payment_options() {
        if (this.frm.doc.mode_of_payment ) {
            this.mode_of_payment_doc = await frappe.db.get_doc("Mode of Payment", this.frm.doc.mode_of_payment);
        } else {
            this.mode_of_payment_doc = {};
        }
    }

    async get_bank_fees_amount(fieldname , mode_of_payment) {
        let bank_fees_amount = 0.00 ;
        bank_fees_amount =  await frappe.db.get_value("Mode of Payment" , mode_of_payment, fieldname).then((r) => {
            return r.message[fieldname]
        });
        return bank_fees_amount
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
            me.frm.add_custom_button(__("Pay Cheque"), () => {
                me.pay_cheque_dialog();
            });
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
            me.frm.add_custom_button(__("Deposit Under Collection"), () => {
                me.create_frappe_prompt([], "optima_payment.cheque.api.deposit_under_collection", __("Deposit Under Collection"), __("Deposit"))
            })
        }
    }

    add_collect_cheque_button() {
        let me = this;
        if (["Deposit Under Collection", "Deposited"].includes(me.frm.doc.cheque_status)) {
            me.frm.add_custom_button(__("Collect"), () => {
                me.collect_cheque_dialog();
            }).css({
                color: 'white',
                background: "green",
            });
        }
    }

    add_return_cheque_button() {
        if (["Deposit Under Collection", "Deposited"].includes(this.frm.doc.cheque_status)) {
            this.frm.add_custom_button(__("Return"), () => {
                let fields = [{ label: __("Remarks"), fieldname: "remarks", fieldtype: "Data", reqd: 1 }]
                this.create_frappe_prompt(fields, "optima_payment.cheque.api.return_cheque", __("Return Cheque"), __("Return"))
            }).css({
                color: 'white',
                background: "orange",
            });
        }
    }

    add_reject_cheque_button() {
        let me = this;
        if (["Deposit Under Collection", "Deposited"].includes(this.frm.doc.cheque_status)) {
            this.frm.add_custom_button(__("Reject"), async () => {
                let fields =  this.get_dialog_fields_return_reject();
                this.create_frappe_prompt(fields, "optima_payment.cheque.api.reject_cheque", __("Reject Cheque"), __("Reject"))
            }).css({
                color: 'white',
                background: "red",
            });
        }
    }

    add_reject_redeposit_and_return_to_holder_button() {
        let me = this;
        if (me.frm.doc.cheque_status === "Rejected") {
            me.frm.add_custom_button(__("Redeposit"), () => {
                frappe.call({
                    method: 'optima_payment.cheque.api.redeposit_cheque',
                    args: {
                        docname: me.frm.doc.name
                    },
                    callback: () => {
                        me.frm.reload_doc();
                    }
                })
            }).css({
                color: 'white',
                background: 'green'
            })
            me.frm.add_custom_button(__("Return To Holder"), () => {
                me.create_frappe_prompt([{ label: __("Remarks"), fieldname: "remarks", fieldtype: "Data", reqd: 1 }], "optima_payment.cheque.api.return_to_holder", __("Return To Holder"), __("Return To Holder"))
            }).css({
                color: 'white',
                background: "red",
            })
        }
    }
    // ====== END OF METHODS ======

    // ===DIALOGS===

    pay_cheque_dialog() {
        let fields = [
            { fieldtype: "Column Break" },
            {
                label: 'Mode of Payment', fieldname: 'mode_of_payment', fieldtype: 'Link', options: 'Mode of Payment', reqd: 1,
                get_query: () => {
                    return {
                        filters: {
                            company: this.frm.doc.company,
                            type: "Bank",
                        }
                    }
                }
            }
        ];
        this.create_frappe_prompt(fields, "optima_payment.cheque.api.pay_cheque", __("Pay Cheque"), __("Pay"));
    }

    collect_cheque_dialog() {
        let me = this;
        let fields = [
            { label: __('Has Bank Commissions'), fieldname: 'has_bank_commissions', fieldtype: 'Check' },
            { fieldtype: "Column Break" },
            {
                label: __('Mode of Payment'), fieldname: 'mode_of_payment',
                fieldtype: 'Link', options: "Mode of Payment",
                reqd: 1 ,
                // depends_on: 'eval: doc.has_bank_fees == 1' , mandatory_depends_on: 'eval: doc.has_bank_fees == 1 ;',
                get_query: () => {
                    return {
                        filters: {
                            company: me.frm.doc.company,
                            type: ["in", ["Bank", "Cash"]],
                        },
                    };
                } ,
                onchange: async  () => {
                    let mode_of_payment = cur_dialog.get_value("mode_of_payment");
                    let bank_fees_amount = await me.get_bank_fees_amount("cheque_collection_fee" , mode_of_payment);
                    cur_dialog.set_value("bank_fees_commission" , bank_fees_amount);
                    // cur_dialog.refresh();
                }
            },
            { 
                label: __('Bank Fees Commission'), 
                fieldname: 'bank_fees_commission', 
                fieldtype: 'Currency', 
                default : 0.00 ,
                // read_only: 1,
                depends_on: 'eval: doc.has_bank_commissions == 1 ;', 
                mandatory_depends_on: 'eval: doc.has_bank_commissions == 1 ;' 
            },
        ]
        this.create_frappe_prompt(fields, "optima_payment.cheque.api.collect_cheque", __("Collect Cheque"), __("Collect"))
    }

    get_dialog_fields_return_reject() {
        let me = this;
        return [
            {
                label: __('Has Bank Fees'),
                fieldname: 'has_bank_fees',
                fieldtype: 'Check',

            },
            {
                fieldtype: "Column Break",
            },
            {
                label: __('Mode of Payment'),
                fieldname: 'mode_of_payment',
                fieldtype: 'Link',
                options: "Mode of Payment",
                depends_on: 'eval: doc.has_bank_fees == 1 ;',
                mandatory_depends_on: 'eval: doc.has_bank_fees == 1 ;',
                get_query: () => {
                    return {
                        filters: {
                            company: me.frm.doc.company,
                            type: "Bank"
                        },
                    };
                },
                onchange: async  () => {
                    let mode_of_payment = cur_dialog.get_value("mode_of_payment");
                    let bank_fees_amount = await me.get_bank_fees_amount("cheque_rejection_fee" , mode_of_payment);
                    cur_dialog.set_value("bank_fees_amount" , bank_fees_amount);
                }
            },
            {
                label: __('Bank Fees Amount'),
                fieldname: 'bank_fees_amount',
                fieldtype: 'Currency',
                default :  0.00 ,
                // read_only : 1,
                depends_on: 'eval: doc.has_bank_fees == 1 ;',
                mandatory_depends_on: 'eval: doc.has_bank_fees == 1 ;',

            },
            {
                fieldtype: "Section Break",
            },
            {
                label: __("Remarks"),
                fieldname: "remarks",
                fieldtype: "Data",
                reqd: 1,
            }
        ]
    }

    // ====== END OF DIALOGS ======


    // ===EVENT HANDLER===

    create_frappe_prompt(fields, method, title, primary_label) {
        let me = this;
        let fd = [{ label: __("Posting Date"), fieldname: "posting_date", fieldtype: "Date", reqd: 1, default: frappe.datetime.now_date() }, ...fields];
        let d = frappe.prompt(
            fd,
            (values) => {
                if (values.posting_date < me.frm.doc.posting_date) {
                    frappe.throw(__("Posting Date should be greater than {0}", [me.frm.doc.posting_date]))
                }
                values["docname"] = me.frm.doc.name;

                frappe.call({
                    method: method,
                    args: values,
                    callback: (r) => {
                        me.frm.reload_doc();
                    }
                })
            },
            __(title),
            __(primary_label),
        )
        const primary_button = d.get_primary_btn();
        switch (primary_label) {
            case "Collect":
                primary_button.css({
                    color: 'white',
                    background: "green",
                });
                break;
            case "Return":
                primary_button.css({
                    color: 'white',
                    background: "orange",
                });
                break;
            case "Reject":
            case "Return To Holder":
                primary_button.css({
                    color: 'white',
                    background: "red",
                });
                break;
        }

    }

    update_property_values(fields) {
        fields.forEach(setting => {
            this.frm.set_df_property(setting.field, setting.property, setting.value);
        });
    }

    // ====== END OF EVENT HANDLER ======

    //  ======  Multi Expense ======

    amount(doc, cdt, cdn) {
        let total = 0;
        this.frm.doc.company_expense.forEach(function (d) {
            total += d.amount;
        });
        this.frm.set_value({ "paid_amount": total, "total_amount": total });
        refresh_field(["total_amount", "paid_amount"]);
    }


    // Change Mandatory
    multi_expense() {
        this.handle_fields_multi_expense();
    }

    handle_fields_multi_expense() {
        let doc = this.frm.doc;
        let fieldSettings = [
            // Fields that require "reqd" to be toggled
            { field: "paid_to", property: "reqd", value: !doc.multi_expense },
            { field: "paid_amount", property: "reqd", value: !doc.multi_expense },
            { field: "received_amount", property: "reqd", value: !doc.multi_expense },
            { field: "base_received_amount", property: "reqd", value: !doc.multi_expense },
            { field: "paid_to_account_currency", property: "reqd", value: !doc.multi_expense },
            { field: "total_taxes_and_charges", property: "hidden", value: doc.multi_expense },
            { field: "party_type", property: "hidden", value: doc.multi_expense },
            { field: "company_expenses", property: "hidden", value: !doc.multi_expense }
        ];
        this.update_property_values(fieldSettings);
    }

}

frappe.ui.form.on("Payment Entry", {
    company(frm) {
        if (frm.doc.company) {
            frappe.call({
                method: "optima_payment.cheque.api.get_company_settings",
                args: {
                    company: frm.doc.company
                },
                callback: (r) => {
                    if (r.message && r.message.enable_optima_payment) {
                        const fieldsToShow = ["is_endorsed_cheque", "multi_expense"]
                        fieldsToShow.forEach(field => {
                            cur_frm.set_df_property(field, "hidden", 0);
                        })
                        if (!cur_frm.cscript["optima_payment.cheque.api.endorsed_cheque"]) {
                            extend_cscript(cur_frm.cscript, new optima_payment.PaymentEntryController({ frm: cur_frm }));
                        }
                    }
                    else {
                        const fieldsToHide = ["is_endorsed_cheque", "multi_expense"]
                        fieldsToHide.forEach(field => {
                            cur_frm.set_df_property(field, "hidden", 1);
                        })
                        cur_frm.set_df_property()
                        cur_frm.cscript = {};
                        cur_frm.refresh();
                    }
                }
            });
        }
    }
});


extend_cscript(cur_frm.cscript, new optima_payment.PaymentEntryController({ frm: cur_frm }));
