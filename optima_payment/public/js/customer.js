frappe.ui.form.on("Customer", {
	refresh(frm) {
		optima_payment.party_statement.add_form_button(frm);
	},
});
