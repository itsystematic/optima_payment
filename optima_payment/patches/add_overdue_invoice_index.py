"""Index Sales Invoice for the Time Based Overdue Limit's overdue-invoice lookup.

Adds to Sales Invoice:
- index customer_company_status_due_date_index (customer, company, status, due_date)
"""

from optima_payment.setup.sync import sync


def execute() -> None:
    sync()
