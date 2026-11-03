# Time Based Overdue Limit — User Guide

A plain-language guide for accountants and implementers to warn about, or stop, new sales to
customers who have left an invoice unpaid too long. For the technical model, see
[reference.md](reference.md).

---

## What it does

You set a rule for a customer, or for a whole customer group: *"once this customer has an invoice
**20 days** past its due date, **warn** the person making a new sale"*, or **block** the sale
instead. The rule is checked on every new **Sales Invoice** and **Sales Order** for that customer.

### Worked example

Today is 02-11-2026. Customer **Al Noor Trading** has one unpaid invoice:

| Invoice | Due date | Outstanding |
|---------|----------|-------------|
| SINV-2026-00041 | 08-10-2026 | 1,150.00 |

It is **25 days** past its due date. Two rules are set for the customer:

| Rule | Action | Threshold Days |
|------|--------|----------------|
| TBOL-00001 | Warn on Save | 20 |
| TBOL-00002 | Block on Save | 30 |

A sales user saves a new Sales Order for Al Noor Trading. 25 days is past TBOL-00001's 20, but not
yet TBOL-00002's 30, so the order **saves** and shows:

> Customer **Al Noor Trading** has Sales Invoice **SINV-2026-00041** overdue by **25** days; it was
> due on 08-10-2026.
> - Rule **TBOL-00001** warns from 20 days overdue.

Five days later the invoice is 30 days overdue, and TBOL-00002 **refuses** the save until the
invoice is paid.

---

## Who can set rules

Only **Accounts Manager** and **System Manager** can create, change or delete rules. Sales Users
and Accounts Users can open them but not change them, so nobody can lift a block on their own
customer or add their own role to the exempt list.

---

## Create a rule (step by step)

1. New **Time Based Overdue Limit**.
2. **Applies To**: *Customer* for one customer, or *Customer Group* for every customer in that
   group and in all the groups under it.
3. **Party**: pick the customer or the group.
4. **Company**: the rule only counts invoices of this company and only checks its documents.
   A new rule starts with your default company. **Clear it** to apply the rule in every company.
5. **Action**: see the table below.
6. **Threshold Days**: how many days past its due date the oldest unpaid invoice must be. The
   rule applies **from** that day: with 20, an invoice 20 days overdue already counts.
7. *(Block actions only)* **Exempt Roles**: users with any of these roles get the warning but are
   not blocked.
8. **Save**. Untick **Enabled** to switch a rule off without deleting it.

A customer can have several rules, for example a 20-day warning and a 30-day block. Two
enabled rules with the same customer or group, company and action are not allowed.

---

## The three actions

| Action | Saving a draft | Submitting |
|--------|----------------|------------|
| **Warn on Save** | Saves, with a warning | Goes through, no message |
| **Block on Save** | **Refused** | **Refused** |
| **Block on Submit** | Saves, with a warning that submit will be refused | **Refused** |

- **Block on Save** also refuses the submit. Otherwise a draft saved before the customer became
  overdue could still be submitted afterwards.
- **Block on Submit** warns at save, so you find out about the block before trying to submit.
- A user with an **exempt role** sees the warning instead of the refusal, at save and at submit.
  Exempt roles have no effect on **Warn on Save**: everybody sees that warning.
- The **Administrator** user holds every role, so is exempt from any rule that lists at least one
  exempt role.

---

## Which rule applies

The most specific rules win, and only those:

1. The customer's **own** rules.
2. If it has none, the rules of **its customer group**.
3. If that group has none, the rules of the **parent group**, then its parent, and so on up the
   tree.

All the rules at that first level apply together. A rule for a different company is ignored and
does not hide the rules above it.

```
Al Noor Trading (no rule) → Retail (no rule) → Commercial: Block on Save, 30 days ← applies
                                                 ↓
                                     All Customer Groups: Warn on Save, 10 days   ← ignored
```

---

## How the days are counted

- Only **submitted Sales Invoices** of the customer, in the document's **company**, with an
  **outstanding amount** and a **due date before today** are counted. Credit notes are not.
- The **oldest** due date among them decides. Newer overdue invoices don't change the count.
- The day count is today minus that due date.
- On an invoice paid in installments, the due date is that of the **last** installment, so an
  earlier installment that is already late is not counted yet.

---

## What is never checked

- **Credit notes** (return invoices), so you can always reduce what the customer owes.
- **POS consolidated invoices**, which POS Closing creates. Blocking them would stop the closing.
- Documents created by **Data Import**, a migration or an app install.
- A customer who, on the company's books, **owes nothing at all**, even if an invoice still shows
  as unpaid. This happens when a payment or credit note was recorded but not allocated to the
  invoice. To clear the invoice itself, match the payment to it with **Payment Reconciliation**.

---

## Things to know

- **A submitted Sales Order does not let its Sales Invoice through.** The invoice is checked on its
  own when it is made.
- **Cancel and amend.** The amended document is a new save, so it is blocked like any other
  unless you hold an exempt role.
- **With Block on Save, a sales user can't even prepare a draft** for an overdue customer. Choose
  **Block on Submit** if drafts should still be allowed.
- **A tiny leftover balance counts.** An invoice with 0.01 outstanding is still unpaid and can
  block. Write such balances off.
- **Background jobs are checked too.** A Sales Invoice made automatically (for example by Auto
  Repeat) for a blocked customer is refused the same way.

---

## Troubleshooting

| Message or symptom | Cause | Fix |
|--------------------|-------|-----|
| *Customer X has Sales Invoice Y overdue by N days … blocks saving and submitting* | A Block on Save rule applies | Collect and record the payment against invoice Y, or ask a user with an exempt role |
| *… blocks submitting* when you submit | A Block on Submit rule applies | As above. The draft stays saved |
| A customer is blocked though they have paid | The payment is recorded but not allocated, and they still owe on another invoice | Allocate the payment with **Payment Reconciliation** |
| *Threshold Days must be greater than 0* | Threshold Days is 0 or empty | Enter a number of days above 0 |
| *Enabled rule … already has the same Applies To, Party, Company and Action* | A second rule repeats an enabled one | Change the existing rule instead, or disable it first |
| A rule never fires in one company | It names a different company | Clear **Company**, or set the right one |
