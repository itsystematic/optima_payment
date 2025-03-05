import frappe

@frappe.whitelist()
def get_or_filtered_accounts(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom OR-based query for the Account doctype.

    Expected client-side usage:
		- doctype = "Account"
		- filters = {
			"company": "Some Company",
			"is_group" : 0
        }

    The OR conditions are:
        (root_type = 'Expense') OR (account_type = 'Tax')
    """
    if not filters.get("company"):
        return []

    company = filters.get("company")
    is_group = filters.get("is_group", 0)

    # We'll do an OR for (root_type = 'Expense' OR account_type = 'Tax')
    query = """
        SELECT
            name
        FROM
            `tabAccount`
        WHERE
            is_group = %s
            AND company = %s
            AND (
                root_type = 'Expense'
                OR
                account_type = 'Tax'
            )
    """

    return frappe.db.sql(
        query,
        (is_group, company),
        as_list=True
    )