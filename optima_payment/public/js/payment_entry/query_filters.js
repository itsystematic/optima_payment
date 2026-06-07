frappe.provide("optima_payment");

optima_payment.QueryFilterManager = class QueryFilterManager {
    constructor(frm) {
        this.frm = frm;
    }

    setup() {
        this.setModeOfPaymentFilter();
        this.setReceivableChequeFilter();
        this.setDefaultAccountFilter();
        this.setPartyTypeFilter();
    }

    setModeOfPaymentFilter() {
        const { PAYMENT_TYPES } = optima_payment.config;

        this.frm.set_query("mode_of_payment", (doc) => {
            let filters =
                doc.payment_type === PAYMENT_TYPES.RECEIVE
                    ? { is_payable_cheque: 0 }
                    : { is_receivable_cheque: 0 };

            if (
                (doc.multi_expense == 1 && doc.payment_type === PAYMENT_TYPES.PAY) ||
                doc.payment_type === PAYMENT_TYPES.INTERNAL_TRANSFER
            ) {
                filters = { is_payable_cheque: 0, is_receivable_cheque: 0 };
            }

            return { filters };
        });
    }

    setReceivableChequeFilter() {
        const { CHEQUE_STATUSES, PAYMENT_TYPES } = optima_payment.config;

        this.frm.set_query("receivable_cheque", (doc) => ({
            filters: {
                docstatus: 1,
                payment_type: PAYMENT_TYPES.RECEIVE,
                cheque_status: CHEQUE_STATUSES.FOR_COLLECTION,
                paid_to_account_currency: doc.paid_from_account_currency,
            },
        }));
    }

    setDefaultAccountFilter() {
        this.frm.set_query("default_account", "company_expense", (doc) => ({
            query: "optima_payment.api.get_or_filtered_accounts",
            filters: {
                disabled: 0,
                is_group: 0,
                company: doc.company,
            },
        }));
    }

    setPartyTypeFilter() {
        this.frm.set_query("party_type", "company_expense", () => ({
            filters: {
                name: ["in", optima_payment.config.PARTY_TYPES_ALLOWED],
            },
        }));
    }
};
