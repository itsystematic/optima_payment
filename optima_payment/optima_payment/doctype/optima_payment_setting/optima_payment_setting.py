# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe import get_app_path


class OptimaPaymentSetting(Document):

    def before_save(self):
        self.enable_print_format()

    def enable_print_format(self):
        print_format_names = get_print_format_names()
        frappe.db.sql(
            """
                UPDATE `tabPrint Format` SET disabled = {0}  WHERE name IN {1}
        """.format(
                not self.enable_optima_payment, tuple(print_format_names)
            ),
            auto_commit=True,
        )


def get_print_format_names():

    app_path = get_app_path("optima_payment", "files", "print_format.json")

    with open(app_path, "r") as file:
        file_data = json.load(file)

    return list(map(lambda x: x.get("name"), file_data))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mode_of_payment(doctype, txt, searchfield, start, page_len, filters):
    
    conditions = ""
    
    if txt : conditions += f"AND mof.name LIKE '{txt}' "

    if filters.get("company") : conditions += f"AND mofa.company = '{filters.get('company')}' "
    if filters.get("default_currency") : conditions += f"AND ac.account_currency = '{filters.get('default_currency')}' "

    return frappe.db.sql("""
        SELECT mof.name , mofa.default_account , ac.account_currency
        FROM `tabMode of Payment` mof
        INNER JOIN `tabMode of Payment Account` mofa ON mof.name = mofa.parent
        LEFT JOIN `tabAccount` ac ON ac.name = mofa.default_account
        WHERE mof.enabled = 1
            {conditions}
    """.format(conditions = conditions))
