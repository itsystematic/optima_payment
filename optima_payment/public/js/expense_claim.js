



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

    },
	onload(frm){
		frm.trigger("get_expense_approver");
	},
    calculate_total_advance_amount(frm) {
        frm.set_value("total_advance_amount", 0.00);
        frm.events.calculate_grand_total(frm);
    },
    employee(frm){
		frm.trigger("get_expense_approver");
	},
	get_expense_approver(frm){
		if(frm.doc.employee){
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Employee",
					name: frm.doc.employee,
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value("expense_approver", r.message.expense_approver);
					}
				}
			})
		}
		else{
			if (!frm.doc.employee){
				frm.set_value("expense_approver", null);
			}
		}
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

        cur_frm.events.calculate_total_advance_amount(frm);
    },
    purchase_invoice(frm, cdt, cdn){
        let current_row = locals[cdt][cdn];
        frappe.db.get_value('Purchase Invoice' , current_row.purchase_invoice , 'outstanding_amount')
            .then(r => {
                current_row.amount = r.message.outstanding_amount ;
                current_row.sanctioned_amount = r.message.outstanding_amount ;
                refresh_field("expenses");
                cur_frm.cscript.calculate_total(frm.doc,cdt,cdn);
                // cur_frm.events.calculate_grand_total(frm);
                cur_frm.events.calculate_total_advance_amount(frm);
            })
    },

});
// Off Original Event and Make New Event 
frappe.ui.form.off("Expense Claim Advance" , "employee_advance");

frappe.ui.form.on("Expense Claim Advance", {
	employee_advance: function (frm, cdt, cdn) {
        
		var child = locals[cdt][cdn];
		if (!frm.doc.employee) {
			frappe.msgprint(__("Select an employee to get the employee advance."));
			frm.doc.advances = [];
			refresh_field("advances");
		} else {
			return frappe.call({
				method: "hrms.hr.doctype.expense_claim.expense_claim.get_advances",
				args: {
					employee: frm.doc.employee,
					advance_id: child.employee_advance,
				},
				callback: function (r, rt) {
                    let total_advance_amount = cur_frm.doc.advances.map(d => d.allocated_amount ? d.allocated_amount : 0).reduce((a, b) => a + b, 0);
                    let total_outstanding_amount = frm.doc.grand_total - total_advance_amount ;
					if (r.message) {
                        let unclaimed_amount = flt(r.message[0].paid_amount) - flt(r.message[0].claimed_amount);

						child.employee_advance = r.message[0].name;
						child.posting_date = r.message[0].posting_date;
						child.advance_account = r.message[0].advance_account;
						child.advance_paid = r.message[0].paid_amount;
                        child.unclaimed_amount = unclaimed_amount ;
                        child.allocated_amount = unclaimed_amount >= total_outstanding_amount ? total_outstanding_amount : unclaimed_amount;
						frm.trigger("calculate_grand_total");
						refresh_field("advances");
					}
				},
			});
		}
	},
});