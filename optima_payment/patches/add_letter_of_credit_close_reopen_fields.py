"""Apply Letter of Credit close and re-open customizations to existing sites.

Adds to Payment Entry:
- is_lc_close_entry (Check, hidden)

Adds to Letter of Credit:
- pre_close_status (Data, hidden)
- reopen_date (Date, read-only)
"""
from optima_payment.setup.registry import ensure_customizations


def execute():
    ensure_customizations()
