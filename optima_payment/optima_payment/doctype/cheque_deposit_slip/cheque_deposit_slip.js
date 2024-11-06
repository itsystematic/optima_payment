// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt
frappe.provide("optima_payment");
optima_payment.ChequeDepositSlip = class ChequeDepositSlip extends frappe.ui.form.Controller {


    refresh() {
        this.setup_queries();
    }

    validate() {
        this.calculate_total_amount();
    }
    setup_queries() {
        let me = this;
        me.frm.set_query("payment_entry", "cheque_deposit_slip_items", (doc) => {

            let payment_entry = doc.cheque_deposit_slip_items.filter(r => r.payment_entry != undefined).map(r => r.payment_entry);
            return {
                query: "optima_payment.optima_payment.doctype.cheque_deposit_slip.cheque_deposit_slip.get_payment_entries",
                filters: {
                    "names": payment_entry,
                    "company": doc.company,
                    // "cheque_deposit_slip": ["is", "not set"]
                }
            }
        })



        me.frm.set_query("depositors_name", (doc) => {
            return {
                filters: {
                    "company": doc.company
                }
            }
        })
    }


    get_dialog_data() {
        let me = this;
        let list_of_data = [];
        for (let item of me.frm.doc.cheque_deposit_slip_items) {
            if (item.status == "Deposit") {
                list_of_data.push({
                    "name": item.name,
                    "payment_entry": item.payment_entry,
                    "cheque_no": item.cheque_no,
                    "status": item.status,
                    "amount": item.amount,
                    "bank_fees": 0.00
                })
            }
        }

        return list_of_data
    }

    calculate_total_amount() {

        let total_amount = 0;
        this.frm.doc.cheque_deposit_slip_items.forEach(row => { total_amount += row.amount });
        this.frm.set_value("total_amount", total_amount);
    }


    cheque_deposit_slip_items_remove() {
        this.calculate_total_amount();
    }

}


extend_cscript(cur_frm.cscript, new optima_payment.ChequeDepositSlip({ frm: cur_frm }));



