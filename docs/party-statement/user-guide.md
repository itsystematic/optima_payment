# Statement of Account — User Guide

A plain-language guide for accountants and implementers to produce a customer's or a supplier's
statement of account and send it to them. For the technical model, see [reference.md](reference.md).

---

## What the statement shows

For one customer or supplier, one company and one period:

- the **Opening Balance**: what the party owed, or was owed, on the day before the period starts;
- **every invoice and payment** in the period, one line per document, with its debit or credit;
- the **balance after each line**;
- the **Closing Balance**;
- totals: on the report, a closing card and a line for the period (see
  [The report's totals](#the-reports-totals)); on the printed statement, **Total Debit**, **Total
  Credit** and **Outstanding Balance**.

The figures come from your **General Ledger** report, so the two always agree. The Opening Balance
and Closing Balance rows show the same Debit and Credit as the General Ledger's *Opening* and
*Closing (Opening + Total)* rows, and the same balance. Like the General Ledger, the statement leaves
out Journal Entries of type Credit Note and Debit Note, which on these sites only move amounts
within the party's own account.

### DR and CR

Every balance is shown as an amount followed by **DR** or **CR**. A zero balance is settled and
reads **0.00**, with neither.

| Shown as | For a customer | For a supplier |
|----------|----------------|----------------|
| **DR** | The customer owes you | You paid the supplier more than they billed |
| **CR** | The customer paid in advance | You owe the supplier |

On the report, each balance is coloured by what it means for that party. **Green** is the balance
you'd expect, **red** is the unusual one worth a look, and **blue** is settled:

| Balance | Customer | Supplier |
|---------|----------|----------|
| **DR** | green | red |
| **0.00** | blue | blue |
| **CR** | red | green |

The printed statement and the emailed copy go to the party, so they carry no colours.

### Worked example

Customer *Al Noor Trading*, period 01-01-2026 to 30-06-2026, owing 1,000.00 at the end of 2025:

| Date | Voucher Type | Voucher No. | Debit | Credit | Balance |
|------|--------------|-------------|-------|--------|---------|
| | **Opening Balance** | | **1,000.00** | - | **1,000.00 DR** |
| 18-01-2026 | Payment Entry | PAY-2026-00012 | - | 1,500.00 | 500.00 CR |
| 19-01-2026 | Sales Invoice | SINV-2026-00031 | 800.00 | - | 300.00 DR |
| | **Closing Balance** | | **1,800.00** | **1,500.00** | **300.00 DR** |

The printed statement shows a zero debit or credit as **-**; the report leaves the cell empty. As in
the General Ledger, the report names the currency once in each amount's header, such as
**Debit (SAR)**, and shows the amounts as plain numbers.

On the printed statement: Total Debit 800.00, Total Credit 1,500.00, Outstanding Balance
**300.00 DR**. The totals cover the period only; the Closing Balance row adds the opening to them,
as the General Ledger does.

### The report's totals

Above the lines, the report shows a plain line for the period, just under the filters, and a card
with the Closing Balance row. For the example:

> For the period 01-01-2026 to 30-06-2026: total debit: 800.00, total credit: 1,500.00, net: 700.00 CR.

| Closing Debit | Closing Credit | Closing Balance |
|---------------|----------------|-----------------|
| 1,800.00 | 1,500.00 | **300.00 DR** |

- The **card** adds up: 1,800.00 − 1,500.00 = 300.00 DR. Only its balance is coloured.
- The **line** holds what happened in the period alone: 800.00 − 1,500.00 = 700.00 CR. Its net is not
  the outstanding balance, because it leaves out the opening.

Closing Debit and Closing Credit are the General Ledger's own Closing row. On sites whose ledger
shows every earlier debit and credit in its Opening row, they are the totals since the account
opened, so they can be much larger than the period's.

---

## Open a statement

1. Open the **Customer** or **Supplier**.
2. Click **View ▸ Statement of Account**. The **Customer Statement** (or **Supplier Statement**)
   report opens for that party and your default company.
3. Check the filters:
   - **Company** — required; a statement covers one company.
   - **From Date** — defaults to the start of the current fiscal year.
   - **To Date** — defaults to today.

The report shows the lines, with the period line and the closing card above them. You can also open
**Customer Statement** or **Supplier Statement** from the search bar and pick the party there.

---

## Preview, print and send

Click **Preview** on the report. The preview page shows the statement exactly as the party will
receive it: your company's name at the top, with the company's **Company Name In Arabic** below it
when that is filled in, the title *Statement of Account*, the party and the period, the lines, and
the three totals. The party, company and dates at the top of the page can be changed there too; the
preview refreshes by itself.

| Button | What it does |
|--------|--------------|
| **Send Email** | Prepares the statement as a PDF and opens the email window, addressed to the party's email, with the PDF already attached and ticked. Choose an email template if you have one, then **Send** |
| **Print** | Prints the statement. To keep a PDF, choose **Save as PDF** as the printer in the print window |
| **Export to Excel** | Downloads the same statement as `Statement-<party>-<to date>.xlsx`, with the DR / CR side in its own column |
| **Open Report** | Goes back to the report with the same filters |

A sent statement appears on the party's timeline, under its activity.

### Language

The statement follows **your** language. With Arabic as your language, the printout and the email
attachment are in Arabic and read right to left. To send an English statement from an Arabic
desk, switch your language first (avatar ▸ **My Settings** ▸ **Language**).

---

## Who can use it

Users with **Accounts User**, **Accounts Manager**, **Optima Payment User** or **Optima Payment
Manager** can open the reports and the preview page, for the customers or suppliers they can see.
Sending email also needs permission to email the customer or supplier.

---

## Troubleshooting

| Message or symptom | What to do |
|--------------------|------------|
| *Set Customer first* (or Company, From Date, To Date) | Fill the named filter |
| *From Date must be on or before To Date* | Swap the dates |
| *You are not permitted to open the Customer Statement report* | Ask for one of the roles above |
| The email window has no address | The party has no primary contact email. Type the address, or set one on the party's primary contact |
| Amounts look different from an invoice's grand total | The statement shows what was posted to the party's account. A credit note, a write-off or an exchange difference shows on its own line |

---

## Related

- [Reference](reference.md) — how the statement is built.
- ERPNext's **General Ledger** report shows the same figures with every account column.
