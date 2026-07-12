frappe.ui.form.on('Bank Account', {
   
     setup: function(frm) {
        frm.trigger("query_filters");
     },

    query_filters(frm) {
        frm.set_query('providing_letter_of_credit_account', function() {
            return {
                filters: {
                    'is_group': 0,
                    'root_type': 'Asset',
                }
            }
        });

        frm.set_query('receiving_letter_of_credit_account', function() {
            return {
                filters: {
                    'is_group': 0,
                    'root_type': 'Liability',
                }
            }
        });

        frm.set_query('bank_guarantee_account', function() {
            return {
                filters: {
                    'is_group': 0
                }
            }
        });
    }
})