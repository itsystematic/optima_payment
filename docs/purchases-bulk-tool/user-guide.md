# Purchases Bulk Tool — User Guide

A plain-language guide for accountants and implementers to enter many purchases in one grid and
create the purchase vouchers in one go. For the technical model, see [reference.md](reference.md).

---

## What the tool does

You type one line per purchase: date, supplier, item, qty, rate and VAT template. When you
**Submit** the tool, it creates the vouchers for you, one per supplier, as Purchase Orders,
Purchase Invoices or Purchase Receipts. Afterwards, the **Vouchers** buttons on the tool submit,
cancel or delete them all at once.

- Lines for the **same supplier, same date and same VAT template** go into **one voucher**.
- A different date or VAT template for that supplier starts a **separate voucher**, because a
  voucher has only one date and one tax template.
- It is **all or nothing**: if one voucher can't be created, **none** are.

### Worked example

Tool **PBT-00001**, voucher type Purchase Invoice, VAT template *KSA VAT 15%*:

| Row | Date | Supplier | Item | Qty | Rate | Amount |
|-----|------|----------|------|-----|------|--------|
| 1 | 12-10-2026 | Al Noor Trading | Cement | 1 | 100 | 115 |
| 2 | 12-10-2026 | Gulf Supplies | Steel | 1 | 200 | 230 |
| 3 | 12-10-2026 | Al Noor Trading | Sand | 2 | 150 | 345 |

Submitting it creates two invoices:

```
PBT-00001 ┬→ ACC-PINV-2026-00041  Al Noor Trading  rows 1, 3  (Cement 100 + Sand 2 × 150, total 460)
          └→ ACC-PINV-2026-00042  Gulf Supplies    row 2      (Steel 200, total 230)
```

---

## Before you start

1. **VAT templates** — each row needs a **Purchase Taxes and Charges Template** for your
   company (for example *KSA VAT 15% Buying*). The VAT column only offers your company's
   templates.
2. **Items** — only items marked *Is Purchase Item* can be picked.
3. **Warehouse** — for Purchase Orders and Purchase Receipts of stock items, ERPNext needs a
   warehouse on every line. Fill **Set Target Warehouse** on the tool for all lines, or give a
   row its own **Warehouse**. Service lines need none.

---

## Create vouchers (step by step)

1. New **Purchases Bulk Tool**. Pick the **Company** and the **Voucher Type**.
2. Set the **Posting Date**. Every new row starts with this date; change a row's date if that
   purchase happened on another day.
3. *(Purchase Order / Receipt only)* choose the **Set Target Warehouse**.
4. *(Optional)* tick **Auto Submit Vouchers** to submit the vouchers as well. Leave it unticked to
   get drafts you can review first.
5. Fill the **Items** grid: date, supplier, item, **Qty**, rate and VAT. Qty starts at 1. The
   **Amount** column shows qty × rate, plus VAT.
6. *(Purchase Order / Receipt only, optional)* to put one line in another warehouse, open the
   row (the edit icon at the end of it) and pick its **Warehouse**. A row's own warehouse wins
   over **Set Target Warehouse**; leave it blank to use the tool's.
7. **Save**, then **Submit**.

After submit, every row shows its **Status** and a **Voucher** link that opens the voucher it
went into.

---

## Row status

| Status | Meaning |
|--------|---------|
| **Pending** | The tool hasn't been submitted yet |
| **Draft** | The voucher is a draft (Auto Submit was off, and nobody has submitted it yet) |
| **Submitted** | The voucher is submitted |
| **Cancelled** | The voucher was cancelled: by **Cancel All**, from its own form, or by cancelling the tool |
| **Deleted** | The voucher was deleted: a draft or cancelled one by **Delete All** or from its own form, or a draft by cancelling the tool. The **Voucher** column is emptied |

The buttons, the tool's own cancel and any delete update the status straight away. If you submit
or cancel a voucher from its own form, click **Vouchers → Update Status** to bring the rows up to
date.

> **Why a deleted row loses its voucher.** When the newest voucher of a numbering series is
> deleted, ERPNext gives its number to the next voucher of that series. If the row kept the
> number, the tool would take that new, unrelated voucher for its own. A deleted voucher can still
> be found under **Deleted Documents**.

---

## Manage the vouchers after submit

A submitted tool has a **Vouchers** button group at the top of the form:

| Button | What it does |
|--------|--------------|
| **Update Status** | Reads each voucher's current state back onto the rows. Changes no voucher |
| **Submit All** | Submits every **draft** voucher |
| **Cancel All** | Cancels every **submitted** voucher. Drafts are left alone |
| **Delete All** | Deletes every **draft** and every **cancelled** voucher. Submitted vouchers are left alone |

- Each button asks you to confirm first, except **Update Status**.
- It is **all or nothing**: if one voucher can't be submitted, cancelled or deleted, none of them
  is, and the message names the voucher and its rows.
- **Delete All** also removes cancelled vouchers, so it leaves no record of them. Cancelling the
  tool itself keeps them.
- A cancelled Purchase Invoice or Receipt can only be deleted when **Accounts Settings → Delete
  Accounting and Stock Ledger Entries on deletion of Transaction** is ticked. Otherwise **Delete
  All** stops at it and deletes nothing, drafts included.
- The tool itself stays submitted. You need *Submit* permission on the tool, and your normal
  permission on the vouchers themselves.

---

## Cancelling the tool

**Cancel** on the tool undoes everything it created:

- **Submitted** vouchers are **cancelled**.
- **Draft** vouchers are **deleted**.

If any voucher can't be cancelled, for example because a submitted Payment Entry still points
at the invoice, the whole cancel stops and nothing changes. Cancel those later documents first,
then cancel the tool again.

> **Fixing one voucher.** You don't have to cancel the whole tool to fix one wrong voucher.
> Cancel that voucher from its own form, **Amend** it, fix it and submit the amendment. Then
> click **Vouchers → Update Status** on the tool. Its row shows **Cancelled** and still links to
> the original voucher, not the amendment, and cancelling the tool later leaves the amendment
> alone. To redo every voucher instead, cancel the tool, **Amend** it, fix the rows and submit
> again.

---

## Troubleshooting

If submit or a **Vouchers** button stops with a red message, ERPNext's own reason is shown
first, followed by the tool's summary:

| Message | Cause | Fix |
|---------|-------|-----|
| *Could not create the Purchase Invoice for supplier … dated … (rows …). No voucher was created.* | That voucher failed; the message above it says why (disabled supplier, missing account, closed period…) | Fix the named rows or the master data, then submit again |
| *Disabled Warehouse … cannot be used for this transaction.* | **Set Target Warehouse** is disabled | Pick an active warehouse |
| *Row #…: Warehouse is mandatory for stock Item …* | A stock item on a Purchase Order / Receipt with no warehouse | Fill **Set Target Warehouse**, or that row's **Warehouse** |
| *Could not submit Purchase Invoice … (rows …). No voucher was changed.* (or *cancel*, *delete*) | A **Submit All**, **Cancel All** or **Delete All** stopped at that voucher; the message above it says why | Fix that voucher or its master data, then click the button again |
| *Cannot delete or cancel because Purchase Invoice … is linked with GL Entry …*, above *Could not delete …* | **Delete All** reached a cancelled invoice or receipt, whose ledger entries stay after cancel | Tick **Delete Accounting and Stock Ledger Entries on deletion of Transaction** in Accounts Settings, or delete the drafts one by one from their own forms |
| *Cannot delete or cancel because Purchase Invoice … is linked with Payment Entry …* | A voucher already has later documents | Cancel those documents first, then cancel the tool |

---

## Related

- [reference.md](reference.md) — technical reference (grouping, voucher construction, bulk actions, rollback)
- [testing.md](../development/testing.md) — how the automated tests exercise all of the above
