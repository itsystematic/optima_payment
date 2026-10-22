# Statement of Account — Docs

Everything about the customer and supplier statement of account (كشف حساب): one party's invoices and
payments over a period, with the opening, running and closing balance.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | Opening a statement from the party, reading DR and CR, the preview page, printing, PDF, Excel and email |
| [reference.md](reference.md) | Developers | The General Ledger as the source, the Statement model, the decisions/effects split, rendering, the API and its access check, translations, tests |

The feature is layered on ERPNext's **General Ledger** report, with two Script Reports, **Customer
Statement** and **Supplier Statement**, and the **party-statement** page. It adds no doctype and no
custom field.

See also: [Testing](../development/testing.md) for how the suite is written and run.
