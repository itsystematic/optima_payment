frappe.provide("optima_payment");

optima_payment.DialogFactory = class DialogFactory {
    constructor(frm) {
        this.frm = frm;
    }

    // ================================================================================================
    // DIALOG DEFAULTS AND QUERIES
    // ================================================================================================

    getDefaultCurrency() {
        return this.frm.doc.payment_type == optima_payment.config.PAYMENT_TYPES.RECEIVE
            ? this.frm.doc.paid_to_account_currency
            : this.frm.doc.paid_from_account_currency;
    }

    getDefaultCostCenter() {
        const companySettings = frappe.boot[`default_cost_center_${this.frm.doc.company}`] || {};
        return companySettings[this.getDefaultCurrency()];
    }

    getModeOfPaymentQuery(type) {
        return {
            query: "optima_payment.cheque.api.get_mode_of_payment",
            filters: {
                company: this.frm.doc.company,
                default_currency: this.getDefaultCurrency(),
                type,
            },
        };
    }

    // ================================================================================================
    // DIALOG CONFIGURATIONS
    // ================================================================================================

    payCheque() {
        return {
            fields: [
                { fieldtype: "Column Break" },
                {
                    label: __("Mode of Payment"),
                    fieldname: "mode_of_payment",
                    fieldtype: "Link",
                    options: "Mode of Payment",
                    reqd: 1,
                    get_query: () => this.getModeOfPaymentQuery(optima_payment.config.MODE_OF_PAYMENT_TYPES.BANK),
                },
            ],
            method: "optima_payment.cheque.api.pay_cheque",
            title: "Pay Cheque",
            primaryLabel: "Pay",
        };
    }

    collectCheque() {
        return {
            fields: [
                {
                    label: __("Has Bank Commissions"),
                    fieldname: "has_bank_commissions",
                    fieldtype: "Check",
                },
                { fieldtype: "Column Break" },
                {
                    label: __("Mode of Payment"),
                    fieldname: "mode_of_payment",
                    fieldtype: "Link",
                    options: "Mode of Payment",
                    reqd: 1,
                    get_query: () =>
                        this.getModeOfPaymentQuery([
                            "in",
                            [
                                optima_payment.config.MODE_OF_PAYMENT_TYPES.BANK,
                                optima_payment.config.MODE_OF_PAYMENT_TYPES.CASH,
                            ],
                        ]),
                    onchange: async () => {
                        const modeOfPayment = cur_dialog.get_value("mode_of_payment");
                        const bankFees = await this._getBankFees(
                            "cheque_collection_fee",
                            modeOfPayment
                        );
                        cur_dialog.set_value("bank_fees_commission", bankFees);
                    },
                },
                {
                    label: __("Bank Fees Commission"),
                    fieldname: "bank_fees_commission",
                    fieldtype: "Currency",
                    default: 0.0,
                    depends_on: "eval: doc.has_bank_commissions == 1 ;",
                    mandatory_depends_on: "eval: doc.has_bank_commissions == 1 ;",
                },
                {
                    label: __("Cost Center"),
                    fieldname: "cost_center",
                    fieldtype: "Link",
                    options: "Cost Center",
                    default: this.getDefaultCostCenter(),
                    depends_on: "eval: doc.has_bank_commissions == 1 ;",
                    mandatory_depends_on: "eval: doc.has_bank_commissions == 1 ;",
                    get_query: () => ({
                        filters: {
                            company: this.frm.doc.company,
                            is_group: 0,
                        },
                    }),
                },
            ],
            method: "optima_payment.cheque.api.collect_cheque",
            title: "Collect Cheque",
            primaryLabel: "Collect",
        };
    }

    returnOrRejectCheque(isReject = false) {
        if (!isReject) {
            return {
                fields: [
                    {
                        label: __("Remarks"),
                        fieldname: "remarks",
                        fieldtype: "Data",
                        reqd: 1,
                        default: "شيك مرتد",
                    },
                ],
                method: "optima_payment.cheque.api.return_cheque",
                title: "Return Cheque",
                primaryLabel: "Return",
            };
        }

        return {
            fields: [
                {
                    label: __("Has Bank Fees"),
                    fieldname: "has_bank_fees",
                    fieldtype: "Check",
                    hidden: this.frm.doc.multi_expense == 1,
                },
                { fieldtype: "Column Break" },
                {
                    label: __("Mode of Payment"),
                    fieldname: "mode_of_payment",
                    fieldtype: "Link",
                    options: "Mode of Payment",
                    depends_on: "eval: doc.has_bank_fees == 1 ;",
                    mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
                    get_query: () =>
                        this.getModeOfPaymentQuery(optima_payment.config.MODE_OF_PAYMENT_TYPES.BANK),
                    onchange: async () => {
                        const modeOfPayment = cur_dialog.get_value("mode_of_payment");
                        const bankFees = await this._getBankFees(
                            "cheque_rejection_fee",
                            modeOfPayment
                        );
                        cur_dialog.set_value("bank_fees_amount", bankFees);
                    },
                },
                {
                    label: __("Bank Fees Amount"),
                    fieldname: "bank_fees_amount",
                    fieldtype: "Currency",
                    default: 0.0,
                    depends_on: "eval: doc.has_bank_fees == 1 ;",
                    mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
                },
                {
                    label: __("Cost Center"),
                    fieldname: "cost_center",
                    fieldtype: "Link",
                    options: "Cost Center",
                    default: this.getDefaultCostCenter(),
                    depends_on: "eval: doc.has_bank_fees == 1 ;",
                    mandatory_depends_on: "eval: doc.has_bank_fees == 1 ;",
                },
                { fieldtype: "Section Break" },
                {
                    label: __("Remarks"),
                    fieldname: "remarks",
                    fieldtype: "Data",
                    reqd: 1,
                    default: "شيك مرفوض",
                },
            ],
            method: "optima_payment.cheque.api.reject_cheque",
            title: "Reject Cheque",
            primaryLabel: "Reject",
        };
    }

    returnToHolder() {
        return {
            fields: [
                {
                    label: __("Remarks"),
                    fieldname: "remarks",
                    fieldtype: "Data",
                    reqd: 1,
                    default: "شيك مرفوض",
                },
            ],
            method: "optima_payment.cheque.api.return_to_holder",
            title: "Return To Holder",
            primaryLabel: "Return To Holder",
        };
    }

    depositUnderCollection() {
        return {
            fields: [],
            method: "optima_payment.cheque.api.deposit_under_collection",
            title: "Deposit Under Collection",
            primaryLabel: "Deposit",
        };
    }

    // ================================================================================================
    // DIALOG DATA HELPERS
    // ================================================================================================

    async _getBankFees(fieldname, modeOfPayment) {
        const response = await frappe.db.get_value("Mode of Payment", modeOfPayment, fieldname);
        return response.message[fieldname] ?? 0;
    }
};
