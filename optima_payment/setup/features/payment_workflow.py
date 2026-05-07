"""Payment workflow setup owned by Payment Entry and Mode of Payment features."""

from __future__ import annotations


OBSOLETE_PROPERTY_SETTERS = [
    {
        "doctype": "Payment Entry",
        "property": "field_order",
    }
]


def get_custom_fields() -> dict[str, list[dict]]:
    """Return Payment workflow custom fields owned by Optima Payment."""
    return {
        "Mode of Payment": [
            {
                "fieldname": "is_payable_cheque",
                "fieldtype": "Check",
                "insert_after": "accounts",
                "label": "Is Payable Cheque",
                "default": 0,
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_receivable_cheque == 0 ;",
            },
            {
                "fieldname": "is_receivable_cheque",
                "fieldtype": "Check",
                "insert_after": "is_payable_cheque",
                "label": "Is Receivable Cheque",
                "default": 0,
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_payable_cheque == 0 ;",
            },
            {
                "fieldname": "cheque_collection_fee",
                "fieldtype": "Float",
                "label": "Cheque Collection Fee",
                "insert_after": "type",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
            {
                "fieldname": "cheque_rejection_fee",
                "fieldtype": "Float",
                "label": "Cheque Rejection Fee",
                "insert_after": "cheque_collection_fee",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
        ],
        "Payment Entry": [
            {
                "fieldname": "payee_name",
                "fieldtype": "Data",
                "insert_after": "reference_no",
                "label": "Payee Name",
                "no_copy": 0,
                "hidden": 0,
            },
            {
                "fieldname": "cheque_deposit_slip",
                "fieldtype": "Link",
                "label": "Cheque Deposit Slip",
                "options": "Cheque Deposit Slip",
                "insert_after": "mode_of_payment",
                "read_only": 1,
            },
            {
                "fieldname": "bank_name",
                "fieldtype": "Link",
                "insert_after": "reference_date",
                "label": "Bank Name",
                "options": "Bank",
                "no_copy": 0,
                "hidden": 0,
            },
            {
                "fieldname": "cheque_details",
                "fieldtype": "Section Break",
                "insert_after": "clearance_date",
                "label": "Cheque Details",
                "depends_on": "eval: doc.mode_of_payment == 'Receivable Cheque' || doc.mode_of_payment == 'Payable Cheque'",
            },
            {
                "fieldname": "cheque_status",
                "fieldtype": "Select",
                "options": "\nEncashment\nCollected\nIssuance\nFor Collection\nDeposited\nDeposit Under Collection\nRejected\nReturn To Holder\nEndorsed\nIssuance From Endorsed\nCancelled\nReturned",
                "insert_after": "cheque_details",
                "label": "Cheque Status",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "bank_fees_amount",
                "fieldtype": "Currency",
                "insert_after": "cheque_status",
                "label": "Bank Fees Amount",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "multi_expense",
                "fieldtype": "Check",
                "label": "Multi Expense",
                "insert_after": "payment_order_status",
                "depends_on": 'eval: doc.payment_type === "Pay" && doc.is_endorsed_cheque !== 1 ',
            },
            {
                "fieldname": "is_endorsed_cheque",
                "fieldtype": "Check",
                "label": "Is Endorsed Cheque",
                "insert_after": "mode_of_payment",
                "depends_on": "eval: doc.payment_type == 'Pay'",
                "default": 0,
            },
            {
                "fieldname": "receivable_cheque",
                "fieldtype": "Link",
                "options": "Payment Entry",
                "label": "Receivable Cheque",
                "insert_after": "is_endorsed_cheque",
                "depends_on": "eval: doc.is_endorsed_cheque == 1 && doc.payment_type == 'Pay'; ",
                "mandatory_depends_on": "eval: doc.is_endorsed_cheque == 1 && doc.payment_type == 'Pay'; ",
            },
            {
                "label": "Company Expenses",
                "fieldname": "company_expenses",
                "fieldtype": "Section Break",
                "insert_after": "receivable_cheque",
                "depends_on": "eval: doc.multi_expense == 1",
            },
            {
                "fieldname": "company_expense",
                "fieldtype": "Table",
                "label": "Company Expense",
                "options": "Company Expense Details",
                "insert_after": "company_expenses",
            },
            {
                "fieldname": "total_amount",
                "fieldtype": "Float",
                "label": "Total Amount",
                "insert_after": "company_expense",
                "read_only": 1,
            },
        ],
    }


def get_property_setters() -> list[dict]:
    """Return Payment workflow property setters owned by Optima Payment."""
    return [
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "reference_no",
            "property_type": "Data",
            "value": "eval: doc.paid_from",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "reference_date",
            "property_type": "Data",
            "value": "eval: doc.paid_from",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "property": "allow_on_submit",
            "fieldname": "cost_center",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "section_break_12",
            "value": "",
            "property_type": "Data",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "party_section",
            "property_type": "Data",
            "value": 'eval: in_list(["Receive", "Pay"], doc.payment_type) && doc.multi_expense != 1',
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "property": "depends_on",
            "fieldname": "payment_amounts_section",
            "property_type": "Data",
            "value": "eval:(doc.paid_to && doc.paid_from) || doc.multi_expense == 1",
            "doctype_or_field": "DocField",
        },
        {
            "doctype": "Payment Entry",
            "fieldname": "status",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": 1,
        },
        {
            "doctype": "Payment Entry",
            "doctype_or_field": "DocField",
            "fieldname": "cheque_status",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": 1,
        },
    ]
