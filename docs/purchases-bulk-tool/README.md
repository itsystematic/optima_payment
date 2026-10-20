# Purchases Bulk Tool — Docs

Everything about entering many purchase lines in one grid and turning them into purchase vouchers.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | Filling the grid, how rows become vouchers, auto-submit, the Vouchers buttons, cancelling, troubleshooting |
| [reference.md](reference.md) | Developers | Grouping key, voucher construction and warehouse precedence, the all-or-nothing savepoint, bulk actions, the released link, cancel rollback, row statuses |

The feature is layered on **Purchases Bulk Tool**, with the child table **Purchases Bulk Tool
Item**. It creates standard **Purchase Order**, **Purchase Invoice** or **Purchase Receipt**
documents.

See also: [Testing](../development/testing.md) for how the suite is written and run.
