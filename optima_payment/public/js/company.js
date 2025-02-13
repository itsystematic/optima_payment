frappe.ui.form.on("Company", {
    refresh: function(frm) {
        frm.set_query("lost_expense_Bank_guarantee_account", function (doc) {
            return {
                filters: {
                    root_type: "Expense",
                }
            }
        });
    }
});