frappe.provide("frappe.ui.form");

frappe.ui.form.Form = class CustomForm extends frappe.ui.form.Form {
    print_doc() {
        if (this.is_dirty()) {
            frappe.toast({
                message: __(
                    "This document has unsaved changes which might not appear in final PDF. <br> Consider saving the document before printing."
                ),
                indicator: "yellow",
            });
        }

        frappe.route_options = {
            frm: this,
        };
        frappe.set_route("custom_print", this.doctype, this.doc.name);
    }
}