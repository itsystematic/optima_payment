// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Payment Setting", {
    refresh(frm) {
        
        for (let field of cur_frm.meta.fields.filter( r => r.options == "Account")) {
            cur_frm.set_query(field.fieldname, function () {
                return {
                    filters: {
                        is_group: 0,
                    },
                };
            });
        }
	},
});
