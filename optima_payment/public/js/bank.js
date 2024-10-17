frappe.provide("optima_payment");


optima_payment.BankController = class BankController extends frappe.ui.form.Controller {
    refresh() {
        this.init();
    }

    init = async () => {
        let me = this;
        await this.add_print_formats();
        frappe.ui.form.on('Bank Print Format Items', {
            default(frm, cdt, cdn) {
                me.ensure_single_default(frm, cdt, cdn);
            }
        })
    }

    add_print_formats = async () => {
        let me = this;
        if (me.frm.doc.bank_print_format && me.frm.doc.bank_print_format.length > 0) {
            return;  // Exit the function if there are already entries
        }

        try {
            const res = await frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Print Format',
                    fields: ['name', 'doc_type'],
                    filters: [
                        ['doc_type', '=', 'Payment Entry'],
                        ['name', 'like', 'SA-%']
                    ]
                }
            });

            const printFormats = res.message;

            // Clear existing entries in the child table before adding new ones (optional)
            // me.frm.clear_table('bank_print_format'); 

            // Loop through the fetched print formats
            printFormats.filter(format => format.name.includes(this.name)).forEach(format => {
                // Add a new child row
                let row = me.frm.add_child('bank_print_format');

                // Check if the row is correctly created
                if (row) {
                    // Set the fields directly on the row
                    row.print_format = format.name;  // Set print format name
                    row.default = 0;                 // Set default to unchecked
                } else {
                    console.error('Failed to add row to bank_print_format');
                }
            });

            // Refresh the field to show the newly added rows
            me.frm.refresh_field("bank_print_format");
        } catch (err) {
            console.error('Error fetching print formats', err);
        }
    };

    toggle_default = (cdt, cdn) => {
        const currentRow = frappe.get_doc(cdt, cdn);

        if (currentRow.default) {
            // Reset other rows' default to 0
            this.frm.doc.bank_print_format.forEach(row => {
                if (row.name !== currentRow.name) {
                    row.default = 0;
                }
            });

            // Refresh the field to reflect changes
            this.frm.refresh_field('bank_print_format');
        }
    };

    ensure_single_default = (frm, cdt, cdn) => {
        const currentRow = frappe.get_doc(cdt, cdn);
        if (currentRow.default) {
            // Reset 'default' for other rows in the child table
            this.frm.doc.bank_print_format.forEach(row => {
                if (row.name !== currentRow.name) {
                    row.default = 0;  // Uncheck all other rows
                }
            });
            // Refresh the field to reflect changes in the UI
            this.frm.refresh_field('bank_print_format');
        }
    };

    validate = (frm) => {
        if (frm.bank_print_format.length > 0) {
            const currentRow = frm.bank_print_format.find(row => {
                return row.default === 1;
            })
            this.set_default_foramt(currentRow.print_format)
        }
    }

    set_default_foramt = async (default_format) => {
        // const payment_entry = await frappe.db.get_doc('DocType', "Payment Entry");
        const res = await frappe.db.get_value("DocType", "Payment Entry", "default_print_format");
        console.log(res.message);
        // await frappe.db.set_value("DocType", "Payment Entry", 'default_print_format', default_format);
        console.log('Payment Entry Updated.');
    }
}



extend_cscript(cur_frm.cscript, new optima_payment.BankController({ frm: cur_frm }));