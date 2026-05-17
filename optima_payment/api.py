"""Optima Payment API helpers."""

import frappe
from frappe.desk.reportview import get_match_cond


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_or_filtered_accounts(doctype, txt, searchfield, start, page_len, filters):
    """Search company expense accounts while preserving the original Optima filter.

    This override exists because the Company Expense table should offer both:
    - normal Link-style incremental search as the user types
    - Optima's custom account scope: Expense accounts or Tax accounts

    Pagination follows Frappe Link search semantics:
    ``start`` is the zero-based offset and ``page_len`` is the maximum number of rows
    returned for the current request.
    """
    filters = frappe.parse_json(filters) or {}

    if not filters.get("company"):
        return []

    searchfield = searchfield or "name"
    txt = txt or ""

    conditions = [
        "`tabAccount`.is_group = %(is_group)s",
        "`tabAccount`.company = %(company)s",
        "(`tabAccount`.root_type = 'Expense' OR `tabAccount`.account_type = 'Tax')",
    ]
    params = {
        "company": filters["company"],
        "is_group": filters.get("is_group", 0),
        "start": start,
        "page_len": page_len,
        "txt": f"%{txt}%",
        "_txt": txt,
    }

    if "disabled" in filters:
        conditions.append("`tabAccount`.disabled = %(disabled)s")
        params["disabled"] = filters["disabled"]

    search_fields = ["name", "account_name", "account_number"]
    if searchfield not in search_fields:
        search_fields.append(searchfield)

    if txt:
        conditions.append(
            "("
            + " OR ".join(f"ifnull(`tabAccount`.`{field}`, '') LIKE %(txt)s" for field in search_fields)
            + ")"
        )

    # Keep closer matches near the top so the custom query feels like a standard Link field.
    order_by = """
        ORDER BY
            (CASE WHEN LOCATE(%(_txt)s, `tabAccount`.name) > 0 THEN LOCATE(%(_txt)s, `tabAccount`.name) ELSE 99999 END),
            (CASE WHEN LOCATE(%(_txt)s, ifnull(`tabAccount`.account_number, '')) > 0
                THEN LOCATE(%(_txt)s, ifnull(`tabAccount`.account_number, '')) ELSE 99999 END),
            (CASE WHEN LOCATE(%(_txt)s, ifnull(`tabAccount`.account_name, '')) > 0
                THEN LOCATE(%(_txt)s, ifnull(`tabAccount`.account_name, '')) ELSE 99999 END),
            `tabAccount`.idx DESC,
            `tabAccount`.name
    """

    return frappe.db.sql(
        f"""
        SELECT
            `tabAccount`.name,
            `tabAccount`.account_number,
            `tabAccount`.account_name
        FROM `tabAccount`
        WHERE {' AND '.join(conditions)}
            {get_match_cond('Account')}
        {order_by}
        LIMIT %(page_len)s OFFSET %(start)s
        """,
        params,
        as_list=True,
    )