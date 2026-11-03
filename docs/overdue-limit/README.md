# Time Based Overdue Limit — Docs

Everything about warning about or blocking sales to a customer whose invoices have been unpaid too
long past their due date.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | Setting up a rule, the three actions, which rule wins, how the days are counted, exempt roles, what is never checked, troubleshooting |
| [reference.md](reference.md) | Developers | The hooks and when they fire, rule selection by tier, the day-count query, the action table, the GL balance guard, the blank company, known limits, tests |

The feature is layered on **Time Based Overdue Limit**, with the child table **Time Based Overdue
Limit Exempt Role**. It checks standard **Sales Invoice** and **Sales Order** documents when they
are saved and submitted. It is ERPNext's Credit Limit keyed on how long the debt has been overdue
instead of how large it is.

See also: [Testing](../development/testing.md) for how the suite is written and run.
