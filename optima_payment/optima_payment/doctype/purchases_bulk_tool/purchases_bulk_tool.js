// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchases Bulk Tool", {
    setup(frm) {
        frm.set_query("set_warehouse", function () {
            return {
                filters: {
                    company: frm.doc.company,
                    is_group: 0,
                },
            };
        });

        frm.set_query("vat", "items", function () {
            return {
                filters: {
                    company: frm.doc.company,
                },
            };
        });

        frm.set_query("item", "items", function () {
            return {
                filters: {
                    is_purchase_item: 1,
                },
            };
        });

        frm.set_query("warehouse", "items", function () {
            return {
                filters: {
                    company: frm.doc.company,
                    is_group: 0,
                },
            };
        });
    },

    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        const group = __("Vouchers");
        frm.add_custom_button(__("Update Status"), () => call_vouchers_api(frm, "update_statuses"), group);

        for (const [action, label, question] of [
            ["submit", __("Submit All"), __("Submit every draft voucher? If one fails, none is submitted.")],
            ["cancel", __("Cancel All"), __("Cancel every submitted voucher? If one fails, none is cancelled.")],
            ["delete", __("Delete All"), __("Delete every draft and cancelled voucher? If one fails, none is deleted.")],
        ]) {
            frm.add_custom_button(
                label,
                () => frappe.confirm(question, () => call_vouchers_api(frm, "run_bulk_action", { action })),
                group
            );
        }
    },
});

frappe.ui.form.on("Purchases Bulk Tool Item", {
    items_add(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "voucher_posting_date", frm.doc.posting_date);
    },

    qty: set_amount,
    rate: set_amount,
    vat: set_amount,
});

function set_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    frappe.call({
        method: "optima_payment.purchases_bulk.api.get_vat_rate",
        args: { template: row.vat },
        callback(r) {
            const amount = flt(row.qty) * flt(row.rate) * (1 + flt(r.message) / 100);
            frappe.model.set_value(cdt, cdn, "amount", flt(amount, precision("amount", row)));
        },
    });
}

function call_vouchers_api(frm, method, args = {}) {
    frappe.call({
        method: `optima_payment.purchases_bulk.api.${method}`,
        args: { tool: frm.doc.name, ...args },
        freeze: true,
        callback() {
            frm.reload_doc();
        },
    });
}
