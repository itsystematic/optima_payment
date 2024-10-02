

frappe.listview_settings['Payment Entry'].add_fields = ["cheque_status", "from_slip", "payment_type"]

frappe.listview_settings['Payment Entry'].get_indicator = (doc) => {

    let status_color = {
        Draft: "red",
        Submitted: "blue",
        Deposited: "green",
        Collected: "green",
        Encashment: "orange",
        Issuance: "green",
        Rejected: "red",
        Returned: "red",
        "For Collection": "yellow",
        "Return To Customer": "red",
        "Deposit Under Collection": "blue",
        "Cancelled": "red",
        "Return To Holder": "red",
        "Endorsed": "purple",
        "Issuance From Endorsed": "green",
    };
    if (doc.cheque_status) {
        return [__(doc.cheque_status), status_color[doc.cheque_status], "status,=," + doc.cheque_status];
    }
    
}

