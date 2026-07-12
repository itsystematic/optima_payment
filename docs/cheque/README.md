# Cheque — Docs

Everything about the post-dated cheque (PDC) lifecycle.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | Receiving/depositing/collecting customer cheques, issuing supplier cheques, deposit slips, printing |
| [reference.md](reference.md) | Developers | The `cheque_status` state machine on Payment Entry, actions, GL builders, supporting doctypes, module map |

The cheque feature is layered on **Payment Entry** (not a dedicated doctype), with supporting
doctypes **Cheque Deposit Slip** and **Cheque Action Log**.
