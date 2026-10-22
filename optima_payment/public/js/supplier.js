frappe.ui.form.on("Supplier", {
	refresh(frm) {
		optima_payment.party_statement.add_form_button(frm);
	},
});
