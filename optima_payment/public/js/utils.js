frappe.provide("optima_payment.utils");

// Clears `fields` on `frm` - generic, no doctype-specific assumptions.
optima_payment.utils.clear_fields = function (frm, fields) {
    fields.forEach((field) => frm.set_value(field, ""));
};

// Single source of truth for Bank Guarantee-BG status colors - shared by the
// form indicator, the list view, and the report formatter so the three stay in sync.
optima_payment.utils.bank_guarantee_status_colors = {
    "New": "gray",
    "Exists": "cyan",
    "Issued": "blue",
    "Extended": "orange",
    "Expired": "yellow",
    "Returned": "green",
    "Lost": "red",
};

// Single source of truth for Letter of Credit status colors - shared by the
// form indicator, the list view, and the report formatter so the three stay in sync.
// Shares colors with bank_guarantee_status_colors for the statuses both doctypes have in
// common; "Closed" (LC's terminal state instead of "Lost") gets its own color.
optima_payment.utils.lc_status_colors = {
    "New": "gray",
    "Exists": "cyan",
    "Issued": "blue",
    "Extended": "orange",
    "Expired": "yellow",
    "Returned": "green",
    "Closed": "purple",
};
