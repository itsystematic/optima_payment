from frappe import _
from erpnext.selling.doctype.sales_order.sales_order_dashboard import get_data as _get_data


def get_data(data=None):
    data = _get_data()
    data["non_standard_fieldnames"]["Letter of Credit"] = "reference_docname"
    data["transactions"][4]["items"].append("Letter of Credit")
    return data
