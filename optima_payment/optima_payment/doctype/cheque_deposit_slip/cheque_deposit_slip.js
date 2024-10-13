// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt
frappe.provide("optima_payment");

optima_payment.ChequeDepositSlip = class ChequeDepositSlip extends frappe.ui.form.Controller {


    refresh() {
        this.setup_queries();
        this.setup_custom_buttons();
    }

    setup_queries() {
        let me = this;

        me.frm.set_query("payment_entry", "cheque_deposit_slip_items", (doc) => {

            let payment_entry = doc.cheque_deposit_slip_items.filter(r => r.payment_entry != undefined).map(r => r.payment_entry);
            return {
                query: "optima_payment.optima_payment.doctype.cheque_deposit_slip.cheque_deposit_slip.get_payment_entries",
                filters: {
                    "names": payment_entry,
                    "company": doc.company
                }
            }
        })

        me.frm.set_query("bank_account", (doc) => {
            return {
                filters: {
                    "company": doc.company
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

    setup_custom_buttons() {
        let me = this;

        if (me.frm.doc.docstatus > 0) {
            me.frm.add_custom_button(
                __("Ledger"),
                function () {
                    frappe.route_options = {
                        voucher_no: me.frm.doc.name,
                        from_date: me.frm.doc.posting_date,
                        to_date: moment(me.frm.doc.modified).format("YYYY-MM-DD"),
                        company: me.frm.doc.company,
                        group_by: "",
                        show_cancelled_entries: me.frm.doc.docstatus === 2,
                    };
                    frappe.set_route("query-report", "General Ledger");
                },
                __("View")
            );

            // me.frm.add_custom_button(__("Update Cheque Status") ,() => {
            //     me.cheque_status_dialog();
            // })
        }
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


    // payment_entry(doc, cdt, cdn) {
    //     let me = this;
    //     let row = frappe.get_doc(cdt, cdn);
    //     if (row.payment_entry) {
    //         frappe.call({
    //             method: "optima_payment.optima_payment.doctype.cheque_deposit_slip.cheque_deposit_slip.get_payment_details",
    //             args: {
    //                 payment_entry: row.payment_entry
    //             },
    //             callback: (r) => {
    //                 if (r.message) {
    //                     console.log(r.message);
    //                     frappe.model.set_value(cdt, cdn, {
    //                         "cheque_no": r.message.reference_no,
    //                         "payee_name": r.message.payee_name,
    //                         "amount": r.message.paid_amount,
    //                         "bank_name": r.message.bank,
    //                         "paid_to": r.message.paid_to,
    //                         "payment_type": r.message.payment_type,
    //                         "posting_date": r.message.posting_date,
    //                         "company": r.message.company
    //                     });
    //                     me.calculate_total_amount();
    //                 } else {
    //                     frappe.msgprint(__("Failed to fetch payment entry details. Please try again."));
    //                 }
    //             }
    //         });
    //     }
    // }


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



