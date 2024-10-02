# create custom fields for mode of payment and payment entry in optima payment 
# create property setter for payment entry in optima payment

def get_custom_fields():
    custom_fields = {
        "Mode of Payment": [
            {
                "fieldname": "is_payable_cheque",
                "fieldtype": "Check",
                "insert_after": "accounts",
                "label": "Is Payable Cheque",
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_receivable_cheque == 0 ;",
            },
            {
                "fieldname": "is_receivable_cheque",
                "fieldtype": "Check",
                "insert_after": "is_payable_cheque",
                "label": "Is Receivable Cheque",
                "depends_on": "eval: doc.type == 'Cheque' && doc.is_payable_cheque == 0 ;",
            },
            {
                "fieldname": "cheque_collection_fee",
                "fieldtype": "Float" ,
                "label" : "Cheque Collection Fee" ,
                "insert_after": "type",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
            {
                "fieldname": "cheque_rejection_fee",
                "fieldtype": "Float" ,
                "label" : "Cheque Rejection Fee" ,
                "insert_after": "cheque_collection_fee",
                "depends_on": "eval: doc.type == 'Bank' ;",
            },
        ],
        "Payment Entry": [
            {
                "fieldname": "cheque_details",
                "fieldtype": "Section Break",
                "insert_after": "mode_of_payment",
                "label": "Cheque Details",
                "depends_on": "eval: doc.mode_of_payment == 'Receivable Cheque' || doc.mode_of_payment == 'Payable Cheque'",
            },
            {
                "fieldname": "beneficiary_name",
                "fieldtype": "Data",
                "insert_after": "cheque_details",
                "label": "Beneficiary Name",
                "no_copy": 1,
            },
            {
                "fieldname": "bank_name",
                "fieldtype": "Link",
                "insert_after": "beneficiary_name",
                "label": "Bank Name",
                "options": "Bank",
                "no_copy": 1,
            },
            {
                "fieldname": "columnklmadjfajkgjkdjnfkvn",
                "fieldtype": "Column Break",
                "insert_after": "bank_name",
                "label": "",
            },
            {
                "fieldname": "cheque_status",
                "fieldtype": "Select",
                "options": "\nEncashment\nCollected\nIssuance\nFor Collection\nDeposited\nDeposit Under Collection\nRejected\nReturn To Customer\nReturn To Holder\nEndorsed\nCancelled",
                "insert_after": "columnklmadjfajkgjkdjnfkvn",
                "label": "Cheque Status",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "pay_mode_of_payment",
                "fieldtype": "Link",
                "options": "Mode of Payment",
                "insert_after": "cheque_status",
                "label": "Pay Mode of Payment",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "against_payment_entry",
                "fieldtype": "Link",
                "options": "Payment Entry",
                "insert_after": "pay_mode_of_payment",
                "label": "Endorsed Cheque",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "bank_fees_amount",
                "fieldtype": "Currency",
                "insert_after": "against_payment_entry",
                "label": "Bank Fees Amount",
                "read_only": 1,
                "no_copy": 1,
            },
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
                "depends_on": "eval: doc.mode_of_payment == 'Payable Cheque'",
                "default": 0
            },
            {
                "fieldname": "receivable_cheque",
                "fieldtype": "Link",
                "options": "Payment Entry",
                "label": "Receivable Cheque",
                "insert_after": "is_endorsed_cheque",
                "depends_on": "eval: doc.is_endorsed_cheque == 1 && doc.mode_of_payment == 'Payable Cheque'",
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
    }
    return custom_fields

def get_property_setter():
    property_setter = [
        {
            "doctype": "Payment Entry",
            "property": "search_fields",
            "fieldname": "",
            "value": "reference_no",
            "property_type": "Data",
            "for_doctype": True,
            "validate_fields_for_doctype": False,
        },
        {
            "doctype": "Payment Entry",
            "property": "reqd",
            "fieldname": "cost_center",
            "value": 1,
            "property_type": "Check",
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
            "fieldname": "section_break_12",
            "property": "depends_on",
            "property_type": "Data",
            "value": None,
        }
    ]
    return property_setter