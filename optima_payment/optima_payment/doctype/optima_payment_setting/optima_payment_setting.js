// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Payment Setting", {
    refresh(frm) {
        frm.trigger("query_filters");
	},
    query_filters: function (frm , cdt ,cdn) {
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
                    account_currency : current_row.default_currency
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
        })

        frm.set_query("default_mode_of_payment" ,"cheque_accounts",  (doc, cdt ,cdn)  =>  {
            let current_row = frappe.get_doc(cdt , cdn);
            return {
                query : "optima_payment.optima_payment.doctype.optima_payment_setting.optima_payment_setting.get_mode_of_payment",
                filters : {
                    company : doc.company ,
                    default_currency : current_row.default_currency
                }
                // filters: [
                //     ["enabled" , "=" , 1],
                //     ["Mode of Payment Account" , "company" , "=" , doc.company],
                //     ["Account" , "default_currency" , "=" , current_row.default_currency]
                // ]
            }
        })

    },

    before_save(frm) {
        
        let array_of_currency = frm.doc.cheque_accounts.map((row) => row.default_currency );
        let unique_currency = [...new Set(array_of_currency)];

        if (array_of_currency.length >  unique_currency.length ) {
            frappe.throw(__("Please Remove Duplicated Currency")) ;
        }
    }

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
