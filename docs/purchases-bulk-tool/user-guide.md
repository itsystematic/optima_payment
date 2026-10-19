# Purchases Bulk Tool — User Guide

A plain-language guide for accountants and implementers to enter many purchases in one grid and
create the purchase vouchers in one go. For the technical model, see [reference.md](reference.md).

---

## What the tool does

You type one line per purchase: date, supplier, item, rate and VAT template. When you **Submit**
the tool, it creates the vouchers for you, one per supplier, as Purchase Orders, Purchase
Invoices or Purchase Receipts.

- Lines for the **same supplier, same date and same VAT template** go into **one voucher**.
- A different date or VAT template for that supplier starts a **separate voucher**, because a
  voucher has only one date and one tax template.
- It is **all or nothing**: if one voucher can't be created, **none** are.

### Worked example

Tool **PBT-00001**, voucher type Purchase Invoice, VAT template *KSA VAT 15%*:

| Row | Date | Supplier | Item | Rate | Amount |
|-----|------|----------|------|------|--------|
| 1 | 12-10-2026 | Al Noor Trading | Cement | 100 | 115 |
| 2 | 12-10-2026 | Gulf Supplies | Steel | 200 | 230 |
| 3 | 12-10-2026 | Al Noor Trading | Sand | 300 | 345 |

Submitting it creates two invoices:

```
PBT-00001 ┬→ ACC-PINV-2026-00041  Al Noor Trading  rows 1, 3  (Cement 100 + Sand 300, total 460)
          └→ ACC-PINV-2026-00042  Gulf Supplies    row 2      (Steel 200, total 230)
```

---

## Before you start

1. **VAT templates** — each row needs a **Purchase Taxes and Charges Template** for your
   company (for example *KSA VAT 15% Buying*). The VAT column only offers your company's
   templates.
2. **Items** — only items marked *Is Purchase Item* can be picked.
3. **Warehouse** — for Purchase Orders and Purchase Receipts of stock items, ERPNext needs a
   warehouse. Fill **Set Target Warehouse** on the tool; it is copied to every voucher.

---

## Create vouchers (step by step)

1. New **Purchases Bulk Tool**. Pick the **Company** and the **Voucher Type**.
2. Set the **Posting Date**. Every new row starts with this date; change a row's date if that
   purchase happened on another day.
3. *(Purchase Order / Receipt only)* choose the **Set Target Warehouse**.
4. *(Optional)* tick **Auto Submit Vouchers** to submit the vouchers as well. Leave it unticked to
   get drafts you can review first.
5. Fill the **Items** grid: date, supplier, item, rate and VAT. The **Amount** column shows the
   rate plus VAT. The quantity on each voucher line is always **1**.
6. **Save**, then **Submit**.

After submit, every row shows its **Status** and a **Voucher** link that opens the voucher it
went into.

---

## Row status

| Status | Meaning |
|--------|---------|
| **Pending** | The tool hasn't been submitted yet |
| **Draft** | The voucher was created as a draft (Auto Submit was off) |
| **Submitted** | The voucher was created and submitted |
| **Cancelled** | The tool was cancelled and the voucher was cancelled |
| **Deleted** | The tool was cancelled and the draft voucher was deleted |

---

## Cancelling the tool

**Cancel** on the tool undoes everything it created:

- **Submitted** vouchers are **cancelled**.
- **Draft** vouchers are **deleted**.

If any voucher can't be cancelled, for example because a submitted Payment Entry still points
at the invoice, the whole cancel stops and nothing changes. Cancel those later documents first,
then cancel the tool again.

> **Cancel the tool, not the voucher.** While the tool is submitted, a voucher it created can't
> be cancelled or deleted on its own, because the tool still points at it. Cancel the tool
> instead. To redo the entry, **Amend** the cancelled tool, fix the rows and submit again.

---

## Troubleshooting

If submit stops with a red message, ERPNext's own reason is shown first, followed by the tool's
summary:

| Message | Cause | Fix |
|---------|-------|-----|
| *Could not create the Purchase Invoice for supplier … dated … (rows …). No voucher was created.* | That voucher failed; the message above it says why (disabled supplier, missing account, closed period…) | Fix the named rows or the master data, then submit again |
| *Disabled Warehouse … cannot be used for this transaction.* | **Set Target Warehouse** is disabled | Pick an active warehouse |
| *Row #…: Warehouse is mandatory for stock Item …* | A stock item on a Purchase Order / Receipt with no warehouse | Fill **Set Target Warehouse** |
| *Cannot delete or cancel because Purchase Invoice … is linked with Purchases Bulk Tool …* | You tried to cancel a voucher directly | Cancel the tool instead |
| *Cannot delete or cancel because Purchase Invoice … is linked with Payment Entry …* | A voucher already has later documents | Cancel those documents first, then cancel the tool |

---

## Related

- [reference.md](reference.md) — technical reference (grouping, voucher construction, rollback)
- [testing.md](../development/testing.md) — how the automated tests exercise all of the above
