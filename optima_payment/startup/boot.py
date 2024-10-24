import frappe

# Adding Accounts in Optima Payment Setting in Bootinfo For Best Performance
def add_optima_payment_setting(boot_info):

    for optima_payment_setting in frappe.db.get_all("Optima Payment Setting" ,{"enable_optima_payment" : 1}, pluck="name") :
        cheque_accounts = frappe.get_doc("Optima Payment Setting" , optima_payment_setting).get("cheque_accounts")
        boot_info[f"default_cost_center_{optima_payment_setting}"] = { row.default_currency : row.default_cost_center for row in cheque_accounts }