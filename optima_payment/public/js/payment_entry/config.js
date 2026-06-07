frappe.provide("optima_payment.config");

Object.assign(optima_payment.config, {
    PAYMENT_TYPES: {
        PAY: "Pay",
        RECEIVE: "Receive",
        INTERNAL_TRANSFER: "Internal Transfer",
    },
    CHEQUE_STATUSES: {
        ISSUANCE: "Issuance",
        FOR_COLLECTION: "For Collection",
        DEPOSITED: "Deposited",
        DEPOSIT_UNDER_COLLECTION: "Deposit Under Collection",
        REJECTED: "Rejected",
    },
    MODE_OF_PAYMENT_TYPES: {
        CHEQUE: "Cheque",
        BANK: "Bank",
        CASH: "Cash",
    },
    CHEQUE_BUTTON_CLASSES: {
        Collect: "btn-success",
        Deposit: "btn-success",
        "Deposit Under Collection": "btn-success",
        Pay: "btn-success",
        "Pay Cheque": "btn-success",
        Redeposit: "btn-success",
        Return: "btn-warning",
        Reject: "btn-danger",
        "Return To Holder": "btn-danger",
    },
    LEGACY_PAYMENT_ENTRY_FIELDS: [
        "custom_multi_expense",
        "custom_company_expenses",
        "custom_company_expense",
        "custom_total_amount",
    ],
    OPTIMA_TOGGLE_FIELDS: ["is_endorsed_cheque", "multi_expense"],
    PARTY_TYPES_ALLOWED: ["Supplier", "Shareholder", "Employee"],
});
