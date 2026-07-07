// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

// ================================================================================================
// FIELD FETCH WIRING
// ================================================================================================
// Letter of Credit is a fully independent doctype, so the field-fetch wiring that
// ERPNext core ships for similar bank-linked doctypes must be reproduced here explicitly.
frappe.provide("optima_payment.utils");

cur_frm.add_fetch("bank_account", "account", "account");
cur_frm.add_fetch("bank_account", "bank_account_no", "bank_account_no");

// Banking and calculated fields that depend on lc_type ("Providing" vs "Receiving") -
// stale values here would misrepresent the new direction, so they reset on every lc_type change.
const LC_TYPE_DEPENDENT_FIELDS = [
    "bank", "bank_account", "account", "lc_account",
    "lc_percent", "lc_amount","mode_of_payment",
    "bank_rate_", "bank_amount",
    "facilities_rate_", "facility_amount",
    "issue_commission", "issue_commission_amount",
    "banking_facilities", "number_of_deferred_days",
    "validity", "start_date", "end_date", "new_end_date",
];

frappe.ui.form.on('Letter of Credit', {

    // ============================================================================================
    // FORM LIFECYCLE HOOKS
    // ============================================================================================
    setup(frm) {
        frm.trigger("query_filters");
    },

    query_filters(frm) {
        frm.set_query("bank_account", function () {
            return {
                filters: {
                    company: frm.doc.company,
                    bank: frm.doc.bank,
                },
            };
        });

        frm.set_query("project", function () {
            return {
                filters: {
                    customer: frm.doc.customer,
                },
            };
        });

        frm.set_query("reference_docname", function () {
            return {
                filters: {
                    docstatus: 1,
                },
            };
        });

        frm.set_query("lc_account", function () {
            return {
                filters: {
                    is_group: 0,
                },
            };
        });

        frm.set_query("mode_of_payment", function () {
            return {
                query: "optima_payment.optima_payment.doctype.letter_of_credit.letter_of_credit.get_mode_of_payment_by_account",
                filters: { account: frm.doc.account },
            };
        });
    },

    onload(frm) {
        frm.trigger("set_reference_doctype_options");
    },

    refresh(frm) {
        frm.trigger("custom_button");
        frm.trigger("set_beneficiary_name");
        frm.trigger("set_status_indicator");
    },

    // ============================================================================================
    // FIELD EVENT HANDLERS
    // ============================================================================================
    bank(frm) {
        optima_payment.utils.clear_fields(frm, [
            "bank_account",
            "account",
            "lc_account",
            "mode_of_payment",
        ]);
    },

    bank_account(frm) {
        optima_payment.utils.clear_fields(frm, ["mode_of_payment"]);
        frm.trigger("fetch_lc_account");
    },

    start_date(frm) {
        let end_date = frappe.datetime.add_days(frm.doc.start_date, frm.doc.validity - 1);
        frm.set_value("end_date", end_date);
    },

    validity(frm) {
        let end_date = frappe.datetime.add_days(frm.doc.start_date, frm.doc.validity - 1);
        frm.set_value("end_date", end_date);
    },

    bank_rate_(frm) {
        frm.trigger("calculte_bank_amount")
    },

    lc_percent(frm) {
        frm.trigger("calculate_lc_amount")
    },

    lc_amount(frm) {
        frm.trigger("calculte_bank_amount")
        frm.trigger("calculate_custom_facility_amount")
    },

    facilities_rate_(frm) {
        frm.trigger("calculate_custom_facility_amount")
        frm.set_value("bank_rate_", 100 - frm.doc.facilities_rate_)
    },

    issue_commission(frm) {
        optima_payment.utils.clear_fields(frm, ["issue_commission_amount"]);
        frm.trigger("bank_rate_");
    },

    no_of_extended_days(frm) {
        var last_end_date = frappe.datetime.add_days(frm.doc.end_date, frm.doc.no_of_extended_days - 1);
        frm.set_value("new_end_date", last_end_date);
    },

    banking_facilities(frm) {
        optima_payment.utils.clear_fields(frm, ["facilities_rate_", "facility_amount", "bank_facilities_account"]);
        
        if (frm.doc.banking_facilities == "Without Facilities") {
            frm.set_value("bank_rate_", 100);
        }
        else {
            frm.set_value("bank_facilities_account", frm.doc.bank_account);
        }
    },

    lc_type(frm) {
        optima_payment.utils.clear_fields(frm, LC_TYPE_DEPENDENT_FIELDS);
        frm.trigger("set_reference_doctype_options");
        frm.trigger("fetch_lc_account");
    },

    reference_doctype(frm) {
        optima_payment.utils.clear_fields(frm, ["reference_docname", "customer", "supplier", "project", "cost_center", "net_amount", "tax_amount", "amount"]);
    },

    reference_docname: async (frm) => {
        try {
            if (!frm.doc.reference_doctype || !frm.doc.reference_docname) return;

            const reference_docname = await frappe.db.get_doc(frm.doc.reference_doctype, frm.doc.reference_docname);

            frm.set_value("customer", reference_docname.customer);
            frm.set_value("supplier", reference_docname.supplier);
            frm.set_value("project", reference_docname.project);
            frm.set_value("cost_center", reference_docname.cost_center);
            frm.set_value("net_amount", reference_docname.total);
            frm.set_value("tax_amount", reference_docname.total_taxes_and_charges);
            frm.set_value("amount", reference_docname.grand_total);
        }
        catch (e) {
            console.error("An error occurred:", e);
        }
    },

    // ============================================================================================
    // CUSTOM BUTTON ACTIONS
    // ============================================================================================
    custom_button(frm) {
        if (frm.doc.lc_status === "Closed" && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Re-Open'), () => {
                frappe.prompt([
                    {
                        label: 'Re-Open Date',
                        fieldname: 'reopen_date',
                        fieldtype: 'Date',
                        reqd: 1,
                    },
                ], (values) => {
                    frm.call({
                        method: "lc_reopen_action",
                        doc: frm.doc,
                        args: {
                            reopen_date: values.reopen_date,
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })
            }).css({ "background-color": "#2e7d32", "color": "white" })
        }

        let status = ["Returned", "Closed"]
        if (status.includes(frm.doc.lc_status) == false && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Return'), () => {
                frappe.prompt([
                    {
                        label: 'Returned Date',
                        fieldname: 'returned_date',
                        fieldtype: 'Date',
                        reqd: 1
                    },
                ], (values) => {
                    frm.call({
                        method: "lc_return",
                        doc: frm.doc,
                        args: {
                            returned_date: values.returned_date
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })
            }).css({ "background-color": "green", "color": "white" })


            frm.add_custom_button(__('Extend'), () => {
                let isVisible = false;
                frappe.prompt([
                    {
                        label: 'Posting Date',
                        fieldname: 'extend_to_date',
                        fieldtype: 'Date',
                        reqd: 1
                    },
                    {
                        // Section Break ----------------------------------------------
                        fieldtype: "Section Break",
                        fieldname: "section_break_1",
                    },
                    {
                        label: 'Has a Commission?',
                        fieldname: 'has_commission',
                        fieldtype: 'Check',
                        default: 0,
                        hidden: frm.doc.lc_type !== "Providing",
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'Commission Amount',
                        fieldname: 'commission_amount',
                        fieldtype: 'Currency',
                        depends_on: "has_commission",
                        mandatory_depends_on: "has_commission"
                    },
                    {
                        // Section Break ----------------------------------------------
                        fieldtype: "Section Break",
                        fieldname: "section_break_2",
                    },
                    {
                        label: 'Extend Days?',
                        fieldname: 'has_days_extension',
                        fieldtype: 'Check',
                        default: 0,
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'Number of Extended Days',
                        fieldname: 'extended_days',
                        fieldtype: 'Int',
                        depends_on: "has_days_extension",
                        mandatory_depends_on: "has_days_extension"
                    },
                    {
                        // Section Break ----------------------------------------------
                        fieldtype: "Section Break",
                        fieldname: "section_break_3",
                    },
                    {
                        label: 'Extend Amount?',
                        fieldname: 'has_amount_extension',
                        fieldtype: 'Check',
                        default: 0,
                        onchange: function () {
                            optima_payment.utils.clear_fields(this.layout, [
                                    "new_cash_margin_amount",
                                    "new_facilities_amount",
                                    "new_facilities_rate",
                                    "with_facilities",
                                    "lc_amount_extension"
                            ]);
                        }
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'LC Amount Extension',
                        fieldname: 'lc_amount_extension',
                        fieldtype: 'Currency',
                        depends_on: "has_amount_extension",
                        mandatory_depends_on: "has_amount_extension",
                        onchange: function () {
                            recalculate_extend_amounts(this.layout);
                        }
                    },
                    {
                        // Section Break ----------------------------------------------
                        fieldtype: "Section Break",
                        fieldname: "section_break_4",
                        depends_on: "has_amount_extension",
                    },
                    {
                        label: 'With Facilities?',
                        fieldname: 'with_facilities',
                        fieldtype: 'Check',
                        default: 0,
                        onchange: function () {
                            recalculate_extend_amounts(this.layout);
                        }
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'New Facilities Rate',
                        fieldname: 'new_facilities_rate',
                        fieldtype: 'Percent',
                        depends_on: "with_facilities",
                        mandatory_depends_on: "with_facilities",
                        onchange: function () {
                            recalculate_extend_amounts(this.layout);
                        }
                    },
                    {
                        // Section Break ----------------------------------------------
                        fieldtype: "Section Break",
                        fieldname: "section_break_5",
                        depends_on: "has_amount_extension",
                    },
                    {
                        label: 'New Cash Margin Amount',
                        fieldname: 'new_cash_margin_amount',
                        fieldtype: 'Currency',
                        read_only: 1,
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'New Facilities Amount',
                        fieldname: 'new_facilities_amount',
                        fieldtype: 'Currency',
                        read_only: 1,
                        depends_on: "with_facilities",
                    },

                ], (values) => {
                    frm.call({
                        method: "lc_extend_action",
                        doc: frm.doc,
                        args: {
                            has_commission: values.has_commission || false,
                            commission_amount: values.commission_amount || 0,
                            end_date: frappe.datetime.add_days(cur_frm.doc.new_end_date ? cur_frm.doc.new_end_date : cur_frm.doc.end_date, values.extended_days || 0),
                            extended_days: values.extended_days || 0,
                            extend_to_date: values.extend_to_date,
                            has_amount_extension: values.has_amount_extension || false,
                            lc_amount_extension: values.lc_amount_extension || 0,
                            with_facilities: values.with_facilities || false,
                            new_facilities_rate: values.new_facilities_rate || 0,
                            new_cash_margin_amount: values.new_cash_margin_amount || 0,
                            new_facilities_amount: values.new_facilities_amount || 0,
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })

            }).css({ "background-color": "#0070cc", "color": "white" })

            frm.add_custom_button(__('Close'), () => {
                frappe.prompt([
                    {
                        label: 'Close Date',
                        fieldname: 'close_date',
                        fieldtype: 'Date',
                        reqd: 1,
                    },
                    {
                        label: 'Close Amount',
                        fieldname: 'close_amount',
                        fieldtype: 'Currency',
                        reqd: 1,
                    },
                ], (values) => {
                    frm.call({
                        method: "lc_close_action",
                        doc: frm.doc,
                        args: {
                            close_date: values.close_date,
                            close_amount: values.close_amount,
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })
            }).css({ "background-color": "#e65100", "color": "white" })


        }

    },

    // ============================================================================================
    // DERIVED FIELD CALCULATIONS
    // ============================================================================================
    set_status_indicator: function (frm) {
        if (!frm.doc.lc_status) return;

        const color = optima_payment.utils.lc_status_colors[frm.doc.lc_status] || "gray";
        frm.page.set_indicator(__(frm.doc.lc_status), color);
    },
    set_beneficiary_name: function (frm) {
        frm.set_value("name_of_beneficiary", frm.doc.company);
    },
    calculate_lc_amount: function (frm) {
        let lc_amount = frm.doc.amount * (frm.doc.lc_percent / 100);
        frm.set_value("lc_amount", lc_amount);
    },
    calculte_bank_amount: function (frm) {
        let bank_amount = frm.doc.lc_amount * (frm.doc.bank_rate_ / 100);
        frm.set_value("bank_amount", bank_amount);
    },
    calculate_custom_facility_amount: function (frm) {
        let facilities_amount = frm.doc.lc_amount * (frm.doc.facilities_rate_ / 100);
        frm.set_value("facility_amount", facilities_amount);
    },

    // ============================================================================================
    // SHARED HELPERS
    // ============================================================================================
    fetch_lc_account: function (frm) {
        // lc_account's source field on Bank Account depends on lc_type - add_fetch can't
        // express that, so it's fetched manually here instead of a static add_fetch wire.
        if (!frm.doc.bank_account || !frm.doc.lc_type) return;

        const source_field = frm.doc.lc_type === "Providing"
            ? "providing_letter_of_credit_account"
            : "receiving_letter_of_credit_account";

        frappe.db.get_value("Bank Account", frm.doc.bank_account, source_field).then((r) => {
            frm.set_value("lc_account", r.message[source_field]);
        });
    },
    set_reference_doctype_options: function (frm) {

        // Auto-set reference_doctype based on lc_type
        if (frm.doc.lc_type === "Providing") {
            frm.set_value("reference_doctype", "Purchase Order");
        } else {
            frm.set_value("reference_doctype", "Sales Order");
        }
    },

})

// ================================================================================================
// EXTEND DIALOG - DERIVED FIELD CALCULATIONS
// ================================================================================================
// Use this.layout (not this.frm) inside a dialog field's onchange - frappe.prompt dialogs
// have no frm, but Layout#init_field always sets fieldobj.layout to the owning Dialog.
function recalculate_extend_amounts(dialog) {
    const extended_amount = dialog.get_value("lc_amount_extension") || 0;
    const with_facilities = dialog.get_value("with_facilities");
    const facilities_rate = with_facilities ? (dialog.get_value("new_facilities_rate") || 0) : 0;

    dialog.set_value("new_cash_margin_amount", extended_amount * (1 - facilities_rate / 100));
    dialog.set_value("new_facilities_amount", extended_amount * (facilities_rate / 100));
}