



frappe.ui.form.on("Expense Claim", {
    refresh(frm){

		frm.set_query("purchase_invoice", "expenses", function(doc,cdt ,cdn) {
            let current_row = locals[cdt][cdn];
			return {
				filters: {
					is_return: 0,
					docstatus: 1,
					status: ["in" , ["Partly Paid" , "Unpaid" ,"Overdue" ,"Submitted"]],
                    credit_to : current_row.default_account
				}
			};
		});

    }
    
})

frappe.ui.form.on("Expense Claim Detail", {
    amount(frm, cdt, cdn){
        let current_row = locals[cdt][cdn];
        if (frm.doc.amount && frm.doc.purchase_invoice){
            frm.call({
                method : "optima_payment.doc_events.expense_claim.validate_outstanding_amount" ,
                args : {
                    purchase_invoice : current_row.purchase_invoice ,
                    amount : amount.purchase_invoice
                },
            })
        }
    },
    purchase_invoice(frm, cdt, cdn){
        let current_row = locals[cdt][cdn];
        frappe.db.get_value('Purchase Invoice' , current_row.purchase_invoice , 'outstanding_amount')
            .then(r => {
                current_row.amount = r.message.outstanding_amount ;
                current_row.sanctioned_amount = r.message.outstanding_amount ;
                refresh_field("expenses");
                cur_frm.cscript.calculate_total(frm.doc,cdt,cdn);
                cur_frm.events.calculate_grand_total(frm);
            })

    }
});


