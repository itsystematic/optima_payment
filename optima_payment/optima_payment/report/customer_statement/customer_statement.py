# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

from optima_payment.party_statement.api import run_report
from optima_payment.party_statement.statement import CUSTOMER


def execute(filters=None):
    return run_report(CUSTOMER, filters)
