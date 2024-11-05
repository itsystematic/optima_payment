# create custom fields for mode of payment and payment entry in optima payment
# create property setter for payment entry in optima payment
import json

MAIN_ORDER_FIELDS = [
    "type_of_payment",
    "naming_series",
    "payment_type",
    "payment_order_status",
    "multi_expense",
    "column_break_5",
    "posting_date",
    "company",
    "mode_of_payment",
    "is_endorsed_cheque",
    "receivable_cheque",
    "party_section",
    "party_type",
    "party",
    "party_name",
    "book_advance_payments_in_separate_party_account",
    "reconcile_on_advance_payment_date",
    "column_break_11",
    "bank_account",
    "party_bank_account",
    "contact_person",
    "contact_email",
    "transaction_references",
    "reference_no",
    "payee_name",
    "column_break_23",
    "reference_date",
    "bank_name",
    "clearance_date",
    "payment_accounts_section",
    "party_balance",
    "paid_from",
    "paid_from_account_type",
    "paid_from_account_currency",
    "paid_from_account_balance",
    "column_break_18",
    "paid_to",
    "paid_to_account_type",
    "paid_to_account_currency",
    "paid_to_account_balance",
    "payment_amounts_section",
    "paid_amount",
    "paid_amount_after_tax",
    "source_exchange_rate",
    "base_paid_amount",
    "base_paid_amount_after_tax",
    "column_break_21",
    "received_amount",
    "received_amount_after_tax",
    "target_exchange_rate",
    "base_received_amount",
    "base_received_amount_after_tax",
    "section_break_14",
    "get_outstanding_invoices",
    "get_outstanding_orders",
    "references",
    "section_break_34",
    "total_allocated_amount",
    "base_total_allocated_amount",
    "set_exchange_gain_loss",
    "column_break_36",
    "unallocated_amount",
    "difference_amount",
    "write_off_difference_amount",
    "taxes_and_charges_section",
    "purchase_taxes_and_charges_template",
    "sales_taxes_and_charges_template",
    "column_break_55",
    "apply_tax_withholding_amount",
    "tax_withholding_category",
    "section_break_56",
    "taxes",
    "section_break_60",
    "base_total_taxes_and_charges",
    "column_break_61",
    "total_taxes_and_charges",
    "deductions_or_loss_section",
    "deductions",
    "cheque_details",
    "cheque_status",
    "pay_mode_of_payment",
    "bank_fees_amount",
    "company_expenses",
    "company_expense",
    "total_amount",
    "accounting_dimensions_section",
    "project",
    "dimension_col_break",
    "cost_center",
    "section_break_12",
    "status",
    "custom_remarks",
    "remarks",
    "base_in_words",
    "is_opening",
    "column_break_16",
    "letter_head",
    "print_heading",
    "bank",
    "bank_account_no",
    "payment_order",
    "in_words",
    "subscription_section",
    "auto_repeat",
    "amended_from",
    "title",
]


def get_custom_fields():
    custom_fields = {
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
            # {
            #     "fieldname": "pay_mode_of_payment",
            #     "fieldtype": "Link",
            #     "options": "Mode of Payment",
            #     "insert_after": "cheque_status",
            #     "label": "Pay Mode of Payment",
            #     "read_only": 1,
            #     "no_copy": 1,
            # },
            {
                "fieldname": "bank_fees_amount",
                "fieldtype": "Currency",
                "insert_after": "cheque_status",
                "label": "Bank Fees Amount",
                "read_only": 1,
                "no_copy": 1,
            },
            # {
            #     "fieldname": "against_payment_entry",
            #     "fieldtype": "Link",
            #     "options": "Payment Entry",
            #     "insert_after": "bank_fees_amount",
            #     "label": "Endorsed Cheque",
            #     "read_only": 1,
            #     "no_copy": 1,
            # },
            # # --FH
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
                "insert_after": "bank_fees_amount",
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
                #  "precision": "",
            },
            #  END --FH
        ],
        "Expense Claim Detail": [
            # --AM
            {
                "fieldname": "purchase_invoice",
                "fieldtype": "Link",
                "label": "Purchase Invoice",
                "options": "Purchase Invoice",
            }
        ],
        "Bank": [
            # --WS
            {
                "label": "Print Formats",
                "fieldname": "bank_formats",
                "fieldtype": "Section Break",
                "insert_after": "data_import_configuration_section",
            },
            {
                "fieldname": "bank_print_format",
                "fieldtype": "Table",
                "label": "Bank Print Format",
                "options": "Bank Print Format Items",
                "insert_after": "bank_formats",
            },
        ],
    }
    return custom_fields


def get_property_setter():

    property_setter = [
        # {
        #     "doctype": "Payment Entry",
        #     "property": "search_fields",
        #     "fieldname": "",
        #     "value": "reference_no",
        #     "property_type": "Data",
        #     "for_doctype": True,
        #     "validate_fields_for_doctype": False,
        # },
        # {
        #     "doctype": "Payment Entry",
        #     "property": "reqd",
        #     "fieldname": "cost_center",
        #     "value": 0,
        #     "property_type": "Check",
        # },
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
            "property": "field_order",
            "property_type": "Data",
            "value": json.dumps(MAIN_ORDER_FIELDS),
            "doctype_or_field": "DocType",
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
        }
    ]
    return property_setter
