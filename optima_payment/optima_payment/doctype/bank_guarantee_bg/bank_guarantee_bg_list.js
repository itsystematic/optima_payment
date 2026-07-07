frappe.listview_settings["Bank Guarantee-BG"] = {
    add_fields: ["bank_guarantee_status"],

    get_indicator(doc) {
        const color = optima_payment.utils.bank_guarantee_status_colors[doc.bank_guarantee_status] || "gray";
        return [__(doc.bank_guarantee_status), color, "bank_guarantee_status,=," + doc.bank_guarantee_status];
    },
};
