


frappe.ui.form.Form = class FrappeForm extends frappe.ui.form.Form {
	_cancel(btn, callback, on_error, skip_confirm) {
		const me = this;
		const cancel_doc = () => {
			frappe.validated = true;
			me.script_manager.trigger("before_cancel").then(() => {
				if (!frappe.validated) {
					return me.handle_save_fail(btn, on_error);
				}

				var after_cancel = function (r) {
					if (r.exc) {
						me.handle_save_fail(btn, on_error);
					} else {
						frappe.utils.play_sound("cancel");
						me.refresh();
						callback && callback();
						me.script_manager.trigger("after_cancel");
					}
				};
				frappe.ui.form.save(me, "cancel", after_cancel, btn);
			});
		};

		if (skip_confirm) {
			cancel_doc();
		} else {
            let message = this.doctype == "Payment Entry" ? "Permanently Cancel All Transaction in {0}  Are You Sure ?" : "Permanently Cancel {0}?"   ;
			frappe.confirm(
				__(message, [this.docname]),
				cancel_doc,
				me.handle_save_fail(btn, on_error)
			);
		}
	}
}