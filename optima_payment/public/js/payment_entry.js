frappe.provide("optima_payment");

// ================================================================================================
// SHARED PAYMENT ENTRY HELPERS
// ================================================================================================
// These helpers stay in the entrypoint because they are reused across the modular controller setup.

function set_company_expense_totals(frm) {
    let total = 0;
    (frm.doc.company_expense || []).forEach((row) => {
        total += Number(row.amount || 0);
    });
    frm.set_value({ paid_amount: total, received_amount: total, total_amount: total });
    refresh_field(["total_amount", "paid_amount", "received_amount"]);
}

function set_company_expense_cost_center(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    const companyExpenseRows = frm.doc.company_expense || [];

    if (companyExpenseRows.length < 2) {
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Company",
                filters: { name: frm.doc.company },
                fieldname: "cost_center",
            },
            callback: (r) => {
                if (r.message) {
                    frappe.model.set_value(row.doctype, row.name, "cost_center", r.message.cost_center);
                }
            },
        });
        return;
    }

    if (row.parentfield) {
        frm.script_manager.copy_from_first_row(row.parentfield, row, ["cost_center"]);
    }
}

function set_dynamic_labels_safely(frm) {
    const company_currency = frm.doc.company
        ? frappe.get_doc(":Company", frm.doc.company)?.default_currency
        : "";

    frm.set_currency_labels(
        [
            "base_paid_amount",
            "base_received_amount",
            "base_total_allocated_amount",
            "difference_amount",
            "base_paid_amount_after_tax",
            "base_received_amount_after_tax",
            "base_total_taxes_and_charges",
        ],
        company_currency
    );

    frm.set_currency_labels(["paid_amount"], frm.doc.paid_from_account_currency);
    frm.set_currency_labels(["received_amount"], frm.doc.paid_to_account_currency);

    const party_account_currency =
        frm.doc.payment_type == "Receive"
            ? frm.doc.paid_from_account_currency
            : frm.doc.paid_to_account_currency;

    frm.set_currency_labels(
        ["total_allocated_amount", "unallocated_amount", "total_taxes_and_charges"],
        party_account_currency
    );

    const currency_field =
        frm.doc.payment_type == "Receive"
            ? "paid_from_account_currency"
            : "paid_to_account_currency";
    frm.set_df_property("total_allocated_amount", "options", currency_field);
    frm.set_df_property("unallocated_amount", "options", currency_field);
    frm.set_df_property("total_taxes_and_charges", "options", currency_field);
    frm.set_df_property("party_balance", "options", currency_field);

    frm.set_currency_labels(
        ["total_amount", "outstanding_amount", "allocated_amount"],
        party_account_currency,
        "references"
    );

    frm.set_df_property(
        "source_exchange_rate",
        "description",
        "1 " + frm.doc.paid_from_account_currency + " = [?] " + company_currency
    );
    frm.set_df_property(
        "target_exchange_rate",
        "description",
        "1 " + frm.doc.paid_to_account_currency + " = [?] " + company_currency
    );

    frm.refresh_fields();

    const party_currency =
        frm.doc.payment_type === "Receive"
            ? "paid_from_account_currency"
            : "paid_to_account_currency";
    const reference_field = frm.fields_dict.references;
    const reference_grid = reference_field && reference_field.grid;

    if (!reference_grid) {
        console.warn("Payment Entry references grid is unavailable during set_dynamic_labels");
        return;
    }

    ["total_amount", "outstanding_amount", "allocated_amount"].forEach((fieldname) => {
        reference_grid.update_docfield_property(fieldname, "options", party_currency);
    });

    reference_grid.refresh();
}

// ================================================================================================
// CONTROLLER BOOTSTRAP
// ================================================================================================

function ensure_optima_payment_controller(frm) {
    if (!frm.__optima_payment_controller) {
        frm.__optima_payment_controller = new optima_payment.PaymentEntryController({ frm });
        extend_cscript(frm.cscript, frm.__optima_payment_controller);
    }

    return frm.__optima_payment_controller;
}

ensure_optima_payment_controller(cur_frm);
