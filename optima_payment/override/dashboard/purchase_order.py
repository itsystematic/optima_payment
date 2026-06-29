from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order_dashboard import get_data as _get_data


def get_data(data=None):
    data = _get_data()
    data["non_standard_fieldnames"]["Letter of Credit"] = "reference_docname"
    data["transactions"][2]["items"].append("Letter of Credit")
    return data
