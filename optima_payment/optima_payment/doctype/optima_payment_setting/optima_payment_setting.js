// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Payment Setting", {

    // ============================================================================================
    // FORM LIFECYCLE HOOKS
    // ============================================================================================
    setup(frm) {
        frm.trigger("query_filters");
    },

    before_save(frm) {
        frm.trigger("validate_unique_currency");
    },

    // ============================================================================================
    // VALIDATION
    // ============================================================================================
    validate_unique_currency(frm) {
        let array_of_currency = frm.doc.cheque_accounts.map((row) => row.default_currency );
        let unique_currency = [...new Set(array_of_currency)];

        if (array_of_currency.length >  unique_currency.length ) {
            frappe.throw(__("Please Remove Duplicated Currency")) ;
        }
    },

    // ============================================================================================
    // SHARED HELPERS
    // ============================================================================================
    query_filters: function (frm , cdt ,cdn) {
        frm.set_query("bank_guarantee_bank_fees_account", () => {
            return {
                filters: {
                    root_type: "Expense",
                    is_group: 0,
                    company: frm.doc.company,
                }
            };
        });

        frm.set_query("bank_guarantee_loss_expense_account", () => {
            return {
                filters: {
                    root_type: "Expense",
                    is_group: 0,
                    company: frm.doc.company,
                }
            };
        });

        frm.set_query("bank_guarantee_receiving_insurance_account",  ()  =>  {
            return {
                filters : {
                    is_group: 0,
                }
            }
        });

        frm.set_query("bank_guarantee_insurance_account",  ()  =>  {
            return {
                filters : {
                    is_group: 0,
                }
            }
        });

        frm.set_query("bank_fees_expense_account", "cheque_accounts",  (doc, cdt ,cdn)  =>  {
            let current_row = frappe.get_doc(cdt , cdn)
            return {
                filters: {
                    root_type: "Expense",
                    is_group: 0,
                    company : doc.company,
                    account_currency : current_row.default_currency
                },
            };
        });

        frm.set_query("bank_commission_account", "cheque_accounts",  (doc, cdt ,cdn)  =>  {
            let current_row = frappe.get_doc(cdt , cdn)
            return {
                filters: {
                    root_type: "Expense",
                    is_group: 0,
                    company : doc.company ,
                    account_currency : current_row.default_currency
                },
            };
        });

        frm.set_query("incoming_cheque_wallet_account", "cheque_accounts",  (doc, cdt ,cdn)  =>  {
            let current_row = frappe.get_doc(cdt , cdn);
            return {
                filters: {
                    // filter if root type is liability or asset
                    root_type: ["in", ["Liability", "Asset"]],
                    is_group: 0,
                    company : doc.company ,
                    account_currency : current_row.default_currency,
                    account_type : "Bank",
                },
            };
        });

        frm.set_query("default_cost_center" , "cheque_accounts",  (doc, cdt ,cdn)  =>  {
            return {
                filters: {
                    company : doc.company ,
                    is_group: 0 ,
                },
            };
        });

        frm.set_query("default_mode_of_payment" ,"cheque_accounts",  (doc, cdt ,cdn)  =>  {
            let current_row = frappe.get_doc(cdt , cdn);
            return {
                query : "optima_payment.cheque.api.get_mode_of_payment",
                filters : {
                    company : doc.company ,
                    default_currency : current_row.default_currency,
                    type: "Bank"
                }
                // filters: [
                //     ["enabled" , "=" , 1],
                //     ["Mode of Payment Account" , "company" , "=" , doc.company],
                //     ["Account" , "default_currency" , "=" , current_row.default_currency]
                // ]
            }
        });

    },

});


frappe.ui.form.on("Cheque Accounts" , {
    default_currency: (frm, cdt, cdn) => {
        let row = locals[cdt][cdn];
        let array_of_currency = frm.doc.cheque_accounts.filter((r) => r.idx != row.idx).map((row) => row.default_currency );

        if (array_of_currency.includes(row.default_currency)) {
            frappe.throw(__("Currency {0} already exists", [row.default_currency])) ;
        }

    },

    cheque_accounts_add(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.default_currency = "" ;
        frm.refresh_fields();
    }

})
