frappe.provide("optima_payment.utils");

// Clears `fields` on `frm` - generic, no doctype-specific assumptions.
optima_payment.utils.clear_fields = function (frm, fields) {
    fields.forEach((field) => frm.set_value(field, ""));
};
