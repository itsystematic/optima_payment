"""Sales Invoice and Sales Order hooks for the Time Based Overdue Limit."""

from optima_payment.overdue_limit import limit


def before_save(doc, method=None):
    limit.check(doc, limit.SAVE)


def before_submit(doc, method=None):
    limit.check(doc, limit.SUBMIT)
