frappe.listview_settings["Letter of Credit"] = {
    add_fields: ["lc_status"],

    get_indicator(doc) {
        const color = optima_payment.utils.lc_status_colors[doc.lc_status] || "gray";
        return [__(doc.lc_status), color, "lc_status,=," + doc.lc_status];
    },
};
