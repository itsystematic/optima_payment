

frappe.ui.form.ControlLink = class ControlLink extends frappe.ui.form.ControlLink{
	static trigger_change_on_input_event = false;
	make_input() {
		var me = this;
		$(`<div class="link-field ui-front" style="position: relative;">
			<input type="text" class="input-with-feedback form-control">
			<span class="link-btn">
				<a class="btn-open no-decoration" title="${__("Open Link")}">
					${frappe.utils.icon("arrow-right", "xs")}
				</a>
			</span>
		</div>`).prependTo(this.input_area);
		this.$input_area = $(this.input_area);
		this.$input = this.$input_area.find("input");
		this.$link = this.$input_area.find(".link-btn");
		this.$link_open = this.$link.find(".btn-open");
		this.set_input_attributes();
		this.$input.on("focus", function () {
			setTimeout(function () {
				if (me.$input.val() && me.get_options()) {
					let doctype = me.get_options();
					let name = me.get_input_value();
					me.$link.toggle(true);
					if ('doc' in me) {
						if (me.doc.doctype == "Payment Entry" && doctype == "Party Type") {
							me.$link_open.attr("href", "/app/" + name.toLowerCase());
						} else {
							me.$link_open.attr("href", frappe.utils.get_form_link(doctype, name));
						}	
					} else {
						me.$link_open.attr("href", frappe.utils.get_form_link(doctype, name));
					}
				}

				if (!me.$input.val()) {
					me.$input.val("").trigger("input");

					// hide link arrow to doctype if none is set
					me.$link.toggle(false);
				}
			}, 500);
		});
		this.$input.on("blur", function () {
			// if this disappears immediately, the user's click
			// does not register, hence timeout
			setTimeout(function () {
				me.$link.toggle(false);
			}, 500);
		});
		this.$input.attr("data-target", this.df.options);
		this.input = this.$input.get(0);
		this.has_input = true;
		this.translate_values = true;
		this.setup_buttons();
		this.setup_awesomeplete();
		this.bind_change_event();
	}
}