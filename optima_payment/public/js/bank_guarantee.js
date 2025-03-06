cur_frm.add_fetch("bank_account", "bank_guarantee_account", "bank_guarantee_account");
frappe.ui.form.on('Bank Guarantee', {
    onload(frm) {
        frm.trigger("set_reference_doctype_options");
    },
    
    refresh(frm) {
        frm.trigger("custom_button");
        frm.trigger("set_beneficiary_name");
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
        // frm.trigger("facilities_rate_")
    },
    facilities_rate_(frm) {
        frm.trigger("calculate_custom_facility_amount")
        frm.set_value("bank_rate_", 100 - frm.doc.facilities_rate_)
    },
    issue_commission(frm) {
        frm.trigger("bank_rate_");
    },
    no_of_extended_days: function (frm) {
        var last_end_date = frappe.datetime.add_days(cur_frm.doc.end_date, cur_frm.doc.no_of_extended_days - 1);
        cur_frm.set_value("new_end_date", last_end_date);
    },
    banking_facilities: function (frm) {
        if (frm.doc.banking_facilities == "Without Facilities") {
            frm.set_value("bank_rate_", 100);
        }
    },
    bg_type: function (frm) {

        frm.trigger("set_reference_doctype_options");
    },

    reference_doctype: function (frm) {
        frm.trigger("reset_fields");
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

    // functions called by field events    ==================================================================================================================

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
                        label: 'No of Extended Days',
                        fieldname: 'extended_days',
                        fieldtype: 'Int',
                        reqd: 1
                    },
                    {
                        fieldtype: "Column Break",
                    },
                    {
                        label: 'Has a Commission?',
                        fieldname: 'has_commission',
                        fieldtype: 'Check',
                        // onchange: function () {
                        //     // Update the visibility of the "Issue Commission Amount" field
                        //     isVisible = this.get_value();
                        //     const issueCommissionField = this.layout.fields_dict.issue_commission_amount;
                        //     issueCommissionField.df.hidden = !isVisible; // Update the hidden property
                        //     issueCommissionField.refresh(); // Refresh the field to apply changes
                        // }

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
                            has_commission: values.has_commission,
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
    reset_fields: function (frm) {
        
        fields = ["reference_docname", "customer", "supplier", "project", "cost_center", "net_amount", "tax_amount", "amount"];

        fields.forEach((field) => {
            frm.set_value(field, "");
        })
    },

    set_reference_doctype_options: function (frm) {

        // Define all possible options you want to allow for `reference_doctype`
        let baseOptions = ["Sales Order", "Purchase Order", "Purchase Invoice"];

        if (frm.doc.bg_type === "Providing") {
            // If bg_type == "Providing", remove "Purchase Order" from the list
            baseOptions = baseOptions.filter(opt => opt !== "Purchase Order");
        }

        // Convert array into newline-separated string for the Select field
        frm.set_df_property("reference_doctype", "options", baseOptions.join("\n"));
        // frm.set_value("reference_doctype", baseOptions[0]);

        // Force a refresh so the field updates immediately
        frm.refresh_field("reference_doctype");
    }

})

