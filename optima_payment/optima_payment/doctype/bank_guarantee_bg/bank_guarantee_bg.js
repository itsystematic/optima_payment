// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

// ================================================================================================
// FIELD FETCH WIRING
// ================================================================================================
// Bank Guarantee-BG is a fully independent doctype (not a customization of ERPNext's
// core "Bank Guarantee"), so the field-fetch wiring that ERPNext core ships in its own
// bank_guarantee.js must be reproduced here explicitly - it is not inherited.
cur_frm.add_fetch("bank_account", "bank_guarantee_account", "bank_guarantee_account");
cur_frm.add_fetch("bank_account", "account", "account");
cur_frm.add_fetch("bank_account", "bank_account_no", "bank_account_no");
cur_frm.add_fetch("bank_account", "iban", "iban");
cur_frm.add_fetch("bank_account", "branch_code", "branch_code");
cur_frm.add_fetch("bank", "swift_number", "swift_number");

// Banking and calculated fields that depend on bg_type ("Providing" vs "Receiving") -
// stale values here would misrepresent the new direction, so they reset on every bg_type change.
const BG_TYPE_DEPENDENT_FIELDS = [
    "bank", "bank_account", "account", "bank_guarantee_account",
    "bank_guarantee_percent", "bank_guarantee_amount",
    "bank_rate_", "bank_amount",
    "facilities_rate_", "facility_amount",
    "issue_commission", "issue_commission_amount",
    "banking_facilities",
    "validity", "start_date", "end_date", "new_end_date",
];

frappe.ui.form.on('Bank Guarantee-BG', {

    // ============================================================================================
    // FORM LIFECYCLE HOOKS
    // ============================================================================================
    setup(frm) {
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
    },

    onload(frm) {
        frm.trigger("set_reference_doctype_options");
    },

    refresh(frm) {
        frm.trigger("custom_button");
        frm.trigger("set_beneficiary_name");
    },

    // ============================================================================================
    // FIELD EVENT HANDLERS
    // ============================================================================================
    bank(frm) {
        optima_payment.utils.clear_fields(frm, ["bank_account", "account", "bank_guarantee_account"]);
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

    bank_guarantee_percent(frm) {
        frm.trigger("calculate_bank_guarantee_amount")
    },

    bank_guarantee_amount(frm) {
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
        if (frm.doc.banking_facilities == "Without Facilities") {
            frm.set_value("bank_rate_", 100);
        }
        optima_payment.utils.clear_fields(frm, ["facilities_rate_", "facility_amount", "bank_facilities_account"]);
    },

    bg_type(frm) {
        optima_payment.utils.clear_fields(frm, BG_TYPE_DEPENDENT_FIELDS);
        frm.trigger("set_reference_doctype_options");
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
        if (frm.doc.docstatus > 0) {
            frm.add_custom_button(__('Ledger'), function () {
                frappe.route_options = {
                    "voucher_no": frm.doc.name,
                    "from_date": frm.doc.posting_date,
                    "to_date": moment(frm.doc.modified).format('YYYY-MM-DD'),
                    "company": frm.doc.company,
                    "show_cancelled_entries": frm.doc.docstatus === 2,
                    "group_by": ""
                };
                frappe.set_route("query-report", "General Ledger");
            }, __('View'));
        }
        let status = ["Returned", 'Lost']
        if (status.includes(frm.doc.bank_guarantee_status) == false && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Return'), () => {
                frappe.prompt([
                    {
                        label: 'Retured Date',
                        fieldname: 'returned_date',
                        fieldtype: 'Date',
                        reqd: 1
                    },
                ], (values) => {
                    frm.call({
                        method: "bank_guarantee_return",
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
                        label: 'Has a Commission?',
                        fieldname: 'has_commission',
                        fieldtype: 'Check',
                        default: 0,
                        hidden: frm.doc.bg_type !== "Providing",
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'No of Extended Days',
                        fieldname: 'extended_days',
                        fieldtype: 'Int',
                        reqd: 1
                    },
                    {
                        label: 'Issue Commission Amount',
                        fieldname: 'issue_commission_amount',
                        fieldtype: 'Float',
                        depends_on: "has_commission",
                        mandatory_depends_on: "has_commission"
                    },

                ], (values) => {
                    frm.call({
                        method: "make_extend_action",
                        doc: frm.doc,
                        args: {
                            has_commission: values.has_commission || false,
                            amount: values.issue_commission_amount || 0,
                            end_date: frappe.datetime.add_days(cur_frm.doc.new_end_date ? cur_frm.doc.new_end_date : cur_frm.doc.end_date, values.extended_days - 1),
                            days: values.extended_days,
                            extend_to_date: values.extend_to_date
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })

            }).css({ "background-color": "#0070cc", "color": "white" })

            frm.add_custom_button(__('Loss'), () => {
                frappe.prompt([
                    {
                        label: 'Loss Date',
                        fieldname: 'loss_date',
                        fieldtype: 'Date',
                        reqd: 1
                    },
                ], (values) => {
                    frm.call({
                        method: "make_loss_action",
                        doc: frm.doc,
                        args: {
                            loss_date: values.loss_date
                        },
                        callback: (r) => {
                            frm.reload_doc()
                        }
                    })
                })
            }).css({ "background-color": "red", "color": "white" })


        }

    },

    // ============================================================================================
    // DERIVED FIELD CALCULATIONS
    // ============================================================================================
    set_beneficiary_name: function (frm) {
        frm.set_value("name_of_beneficiary", frm.doc.company);
    },
    calculate_bank_guarantee_amount: function (frm) {
        let bank_guarantee_amount = frm.doc.net_amount * (frm.doc.bank_guarantee_percent / 100);
        frm.set_value("bank_guarantee_amount", bank_guarantee_amount);
    },
    calculte_bank_amount: function (frm) {
        let bank_amount = frm.doc.bank_guarantee_amount * (frm.doc.bank_rate_ / 100);
        frm.set_value("bank_amount", bank_amount);
    },
    calculate_custom_facility_amount: function (frm) {
        let facilities_amount = frm.doc.bank_guarantee_amount * (frm.doc.facilities_rate_ / 100);
        frm.set_value("facility_amount", facilities_amount);
    },

    // ============================================================================================
    // SHARED HELPERS
    // ============================================================================================
    set_reference_doctype_options: function (frm) {

        // Auto-set reference_doctype based on bg_type
        if (frm.doc.bg_type === "Providing") {
            frm.set_value("reference_doctype", "Sales Order");
        } else {
            frm.set_value("reference_doctype", "Purchase Order");
        }
    },

})
