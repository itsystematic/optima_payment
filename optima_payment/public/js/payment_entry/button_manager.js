frappe.provide("optima_payment");

optima_payment.ButtonManager = class ButtonManager {
    constructor(frm, dialogFactory, promptFn) {
        this.frm = frm;
        this.dialogFactory = dialogFactory;
        this.promptFn = promptFn;
    }

    addAll(modeOfPaymentDoc = {}) {
        this.modeOfPaymentDoc = modeOfPaymentDoc || {};
        this.addPayableButtons();
        this.addReceivableButtons();
    }

    addPayableButtons() {
        if (!this.shouldShowPayCheque()) {
            return;
        }

        this.addButton("Pay Cheque", () => {
            this.promptFn(this.dialogFactory.payCheque());
        });
    }

    shouldShowPayCheque() {
        const { CHEQUE_STATUSES, MODE_OF_PAYMENT_TYPES, PAYMENT_TYPES } = optima_payment.config;
        const doc = this.frm.doc;

        return (
            this.modeOfPaymentDoc.type === MODE_OF_PAYMENT_TYPES.CHEQUE &&
            this.modeOfPaymentDoc.is_payable_cheque == 1 &&
            doc.payment_type == PAYMENT_TYPES.PAY &&
            doc.docstatus == 1 &&
            !doc.is_endorsed_cheque &&
            doc.cheque_status == CHEQUE_STATUSES.ISSUANCE &&
            frappe.datetime.get_today() >= doc.reference_date
        );
    }

    addReceivableButtons() {
        if (!this.isReceivableChequeDoc()) {
            return;
        }

        this.addDepositUnderCollectionButton();
        this.addCollectButton();
        this.addReturnButton();
        this.addRejectButton();
        this.addRejectedStateButtons();
    }

    isReceivableChequeDoc() {
        const { MODE_OF_PAYMENT_TYPES, PAYMENT_TYPES } = optima_payment.config;
        const doc = this.frm.doc;

        return (
            this.modeOfPaymentDoc.type === MODE_OF_PAYMENT_TYPES.CHEQUE &&
            this.modeOfPaymentDoc.is_receivable_cheque == 1 &&
            doc.payment_type == PAYMENT_TYPES.RECEIVE &&
            doc.docstatus == 1
        );
    }

    addDepositUnderCollectionButton() {
        if (this.frm.doc.cheque_status != optima_payment.config.CHEQUE_STATUSES.FOR_COLLECTION) {
            return;
        }

        this.addButton("Deposit Under Collection", () => {
            this.promptFn(this.dialogFactory.depositUnderCollection());
        });
    }

    addCollectButton() {
        if (!this.isChequeDeposited()) {
            return;
        }

        this.addButton("Collect", () => {
            this.promptFn(this.dialogFactory.collectCheque());
        });
    }

    addReturnButton() {
        if (!this.isChequeDeposited()) {
            return;
        }

        this.addButton("Return", () => {
            this.promptFn(this.dialogFactory.returnOrRejectCheque(false));
        });
    }

    addRejectButton() {
        if (!this.isChequeDeposited()) {
            return;
        }

        this.addButton("Reject", () => {
            this.promptFn(this.dialogFactory.returnOrRejectCheque(true));

            if (this.frm.doc.cheque_deposit_slip) {
                this.frm.doc.cheque_deposit_slip == "";
            }
        });
    }

    addRejectedStateButtons() {
        if (this.frm.doc.cheque_status !== optima_payment.config.CHEQUE_STATUSES.REJECTED) {
            return;
        }

        this.addButton("Redeposit", () => {
            frappe.call({
                method: "optima_payment.cheque.api.redeposit_cheque",
                args: {
                    docname: this.frm.doc.name,
                },
                callback: () => {
                    this.frm.reload_doc();
                },
            });
        });

        this.addButton("Return To Holder", () => {
            this.promptFn(this.dialogFactory.returnToHolder());
        });
    }

    isChequeDeposited() {
        const { DEPOSITED, DEPOSIT_UNDER_COLLECTION } = optima_payment.config.CHEQUE_STATUSES;
        return [DEPOSIT_UNDER_COLLECTION, DEPOSITED].includes(this.frm.doc.cheque_status);
    }

    addButton(label, callback) {
        const btnClass =
            optima_payment.config.CHEQUE_BUTTON_CLASSES[label] || "btn-default";

        this.frm
            .add_custom_button(__(label), callback)
            .removeClass("btn-default")
            .addClass(btnClass);
    }
};
