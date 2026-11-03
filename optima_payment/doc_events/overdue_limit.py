"""Sales Invoice and Sales Order hooks for the Time Based Overdue Limit, one action per hook."""

from optima_payment.overdue_limit import limit


def validate(doc, method=None):
    limit.check(doc, limit.WARN_ON_SAVE)


def before_save(doc, method=None):
    limit.check(doc, limit.BLOCK_ON_SAVE)


def before_submit(doc, method=None):
    limit.check(doc, limit.BLOCK_ON_SUBMIT)
