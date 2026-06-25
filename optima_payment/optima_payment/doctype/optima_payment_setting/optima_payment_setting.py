# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe import get_app_path


class OptimaPaymentSetting(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from optima_payment.optima_payment.doctype.cheque_accounts.cheque_accounts import ChequeAccounts

        bank_guarantee_bank_fees_account: DF.Link | None
        bank_guarantee_insurance_account: DF.Link | None
        bank_guarantee_loss_expense_account: DF.Link | None
        bank_guarantee_receiving_insurance_account: DF.Link | None
        cheque_accounts: DF.Table[ChequeAccounts]
        company: DF.Link
        enable_auto_deposit_under_collection_in_time: DF.Check
        enable_auto_pay_cheque_in_time: DF.Check
        enable_optima_payment: DF.Check
        lc_bank_fees_account: DF.Link | None
        lc_insurance_account: DF.Link | None
        lc_loss_expense_account: DF.Link | None
        lc_receiving_insurance_account: DF.Link | None
    # end: auto-generated types

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



