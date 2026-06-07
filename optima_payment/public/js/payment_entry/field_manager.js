frappe.provide("optima_payment");

optima_payment.FieldVisibilityManager = class FieldVisibilityManager {
    constructor(frm) {
        this.frm = frm;
    }

    computeFieldStates(modeOfPaymentDoc = {}) {
        const doc = this.frm.doc;
        const mop = modeOfPaymentDoc || {};
        const { MODE_OF_PAYMENT_TYPES, PAYMENT_TYPES } = optima_payment.config;
        const isCheque = mop.type === MODE_OF_PAYMENT_TYPES.CHEQUE;
        const hasBankFees = doc.has_bank_fees == 1;

        return {
            is_endorsed_cheque: {
                hidden:
                    doc.payment_type === PAYMENT_TYPES.RECEIVE ||
                    (doc.payment_type === PAYMENT_TYPES.PAY && !isCheque) ||
                    mop.receivable_cheque == 1 ||
                    doc.multi_expense == 1,
            },
            multi_expense: {
                hidden: hasBankFees || isCheque ? 1 : 0,
            },
            payee_name: {
                read_only: doc.is_endorsed_cheque,
                hidden: !isCheque,
                reqd: isCheque,
            },
            bank_name: {
                read_only: doc.is_endorsed_cheque,
                hidden: !isCheque,
                reqd: isCheque,
            },
            paid_to: { reqd: !doc.multi_expense },
            paid_amount: {
                reqd: !doc.multi_expense,
                read_only: doc.is_endorsed_cheque,
            },
            received_amount: {
                reqd: !doc.multi_expense,
                read_only: doc.is_endorsed_cheque,
            },
            base_received_amount: { reqd: !doc.multi_expense },
            paid_to_account_currency: { reqd: !doc.multi_expense },
            total_taxes_and_charges: { hidden: doc.multi_expense },
            party_type: {
                hidden: doc.multi_expense && doc.is_endorsed_cheque == 0,
                reqd: doc.is_endorsed_cheque ? 1 : 0,
            },
            company_expenses: { hidden: !doc.multi_expense },
            party: { reqd: doc.is_endorsed_cheque ? 1 : 0 },
            reference_date: { read_only: doc.is_endorsed_cheque },
            reference_no: { read_only: doc.is_endorsed_cheque },
            paid_from: { read_only: doc.is_endorsed_cheque ? 1 : 0 },
        };
    }

    applyFieldStates(fieldStates) {
        Object.entries(fieldStates).forEach(([fieldname, properties]) => {
            Object.entries(properties).forEach(([property, value]) => {
                this.frm.set_df_property(fieldname, property, value);
            });
        });
    }

    updateAll(modeOfPaymentDoc = {}) {
        const states = this.computeFieldStates(modeOfPaymentDoc);

        if (this.frm.fields_dict.has_bank_fees) {
            states.has_bank_fees = {
                hidden: this.frm.doc.multi_expense == 1,
            };
        }

        this.applyFieldStates(states);
    }

    hideLegacyFields() {
        optima_payment.config.LEGACY_PAYMENT_ENTRY_FIELDS.forEach((fieldname) => {
            if (this.frm.meta?.fields?.some((field) => field.fieldname === fieldname)) {
                this.frm.set_df_property(fieldname, "hidden", 1);
            }
        });
    }

    setOptimaFieldsHidden(hidden) {
        optima_payment.config.OPTIMA_TOGGLE_FIELDS.forEach((fieldname) => {
            if (this.frm.fields_dict?.[fieldname]) {
                this.frm.set_df_property(fieldname, "hidden", hidden ? 1 : 0);
            }
        });
    }
};
