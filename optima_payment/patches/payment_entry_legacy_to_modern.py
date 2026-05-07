import frappe
from click import secho

LEGACY_MULTI_EXPENSE_FIELD = "custom_multi_expense"
LEGACY_TOTAL_AMOUNT_FIELD = "custom_total_amount"
LEGACY_COMPANY_EXPENSE_FIELD = "custom_company_expense"
MODERN_MULTI_EXPENSE_FIELD = "multi_expense"
MODERN_TOTAL_AMOUNT_FIELD = "total_amount"
MODERN_COMPANY_EXPENSE_FIELD = "company_expense"
COMPANY_EXPENSE_CHILD_DOCTYPE = "Company Expense Details"
COMPANY_EXPENSE_CHILD_FIELDS = (
    "default_account",
    "party_type",
    "party",
    "account_currency",
    "account_type",
    "exchange_rate",
    "cost_center",
    "remarks",
    "amount",
)


def execute():
    migrated_multi_expense = migrate_multi_expense_flags()
    migrated_total_amount = migrate_total_amounts()
    cloned_company_expense_rows = clone_company_expense_rows()
    updated_entries_from_rows = backfill_entries_from_company_expense_rows()

    frappe.clear_cache(doctype="Payment Entry")
    frappe.clear_cache(doctype=COMPANY_EXPENSE_CHILD_DOCTYPE)

    secho(
        "Payment Entry legacy migration complete "
        f"(multi_expense={migrated_multi_expense}, total_amount={migrated_total_amount}, "
        f"company_expense_rows={cloned_company_expense_rows}, row_backfills={updated_entries_from_rows})",
        fg="green",
    )


def migrate_multi_expense_flags() -> int:
    if not (
        frappe.db.has_column("Payment Entry", LEGACY_MULTI_EXPENSE_FIELD)
        and frappe.db.has_column("Payment Entry", MODERN_MULTI_EXPENSE_FIELD)
    ):
        return 0

    entries = frappe.get_all(
        "Payment Entry",
        filters={LEGACY_MULTI_EXPENSE_FIELD: 1},
        fields=["name", MODERN_MULTI_EXPENSE_FIELD],
    )

    migrated = 0
    for entry in entries:
        if entry.get(MODERN_MULTI_EXPENSE_FIELD):
            continue

        frappe.db.set_value(
            "Payment Entry",
            entry.name,
            MODERN_MULTI_EXPENSE_FIELD,
            1,
            update_modified=False,
        )
        migrated += 1

    return migrated


def migrate_total_amounts() -> int:
    if not (
        frappe.db.has_column("Payment Entry", LEGACY_TOTAL_AMOUNT_FIELD)
        and frappe.db.has_column("Payment Entry", MODERN_TOTAL_AMOUNT_FIELD)
    ):
        return 0

    entries = frappe.get_all(
        "Payment Entry",
        filters={LEGACY_TOTAL_AMOUNT_FIELD: ["!=", 0]},
        fields=["name", LEGACY_TOTAL_AMOUNT_FIELD, MODERN_TOTAL_AMOUNT_FIELD],
    )

    migrated = 0
    for entry in entries:
        if frappe.utils.flt(entry.get(MODERN_TOTAL_AMOUNT_FIELD)):
            continue

        frappe.db.set_value(
            "Payment Entry",
            entry.name,
            MODERN_TOTAL_AMOUNT_FIELD,
            entry.get(LEGACY_TOTAL_AMOUNT_FIELD),
            update_modified=False,
        )
        migrated += 1

    return migrated


def clone_company_expense_rows() -> int:
    if not has_payment_entry_field(LEGACY_COMPANY_EXPENSE_FIELD) or not has_payment_entry_field(
        MODERN_COMPANY_EXPENSE_FIELD
    ):
        return 0

    legacy_parents = frappe.get_all(
        COMPANY_EXPENSE_CHILD_DOCTYPE,
        filters={
            "parenttype": "Payment Entry",
            "parentfield": LEGACY_COMPANY_EXPENSE_FIELD,
        },
        distinct=True,
        pluck="parent",
    )

    if not legacy_parents:
        return 0

    modern_rows = frappe.get_all(
        COMPANY_EXPENSE_CHILD_DOCTYPE,
        filters={
            "parenttype": "Payment Entry",
            "parentfield": MODERN_COMPANY_EXPENSE_FIELD,
            "parent": ["in", legacy_parents],
        },
        fields=["parent", "idx"],
    )
    modern_row_indexes_by_parent: dict[str, set[int]] = {}
    for row in modern_rows:
        modern_row_indexes_by_parent.setdefault(row.parent, set()).add(int(row.idx))

    legacy_rows = frappe.get_all(
        COMPANY_EXPENSE_CHILD_DOCTYPE,
        filters={
            "parenttype": "Payment Entry",
            "parentfield": LEGACY_COMPANY_EXPENSE_FIELD,
            "parent": ["in", legacy_parents],
        },
        fields=["parent", "idx", *COMPANY_EXPENSE_CHILD_FIELDS],
        order_by="parent asc, idx asc",
    )

    migrated = 0
    for row in legacy_rows:
        modern_indexes = modern_row_indexes_by_parent.setdefault(row.parent, set())
        if int(row.idx) in modern_indexes:
            continue

        child_doc = frappe.get_doc(
            {
                "doctype": COMPANY_EXPENSE_CHILD_DOCTYPE,
                "parent": row.parent,
                "parenttype": "Payment Entry",
                "parentfield": MODERN_COMPANY_EXPENSE_FIELD,
                "idx": row.idx,
                **{fieldname: row.get(fieldname) for fieldname in COMPANY_EXPENSE_CHILD_FIELDS},
            }
        )
        child_doc.flags.ignore_permissions = True
        child_doc.db_insert()
        modern_indexes.add(int(row.idx))
        migrated += 1

    return migrated


def backfill_entries_from_company_expense_rows() -> int:
    if not frappe.db.has_column("Payment Entry", MODERN_MULTI_EXPENSE_FIELD):
        return 0

    rows_by_entry = frappe.db.sql(
        f"""
        SELECT parent, SUM(amount) AS total_amount
        FROM `tab{COMPANY_EXPENSE_CHILD_DOCTYPE}`
        WHERE parenttype = 'Payment Entry'
          AND parentfield = %s
        GROUP BY parent
        """,
        MODERN_COMPANY_EXPENSE_FIELD,
        as_dict=True,
    )

    updated = 0
    for row in rows_by_entry:
        values = {}

        payment_entry = frappe.db.get_value(
            "Payment Entry",
            row.parent,
            [MODERN_MULTI_EXPENSE_FIELD, MODERN_TOTAL_AMOUNT_FIELD]
            if frappe.db.has_column("Payment Entry", MODERN_TOTAL_AMOUNT_FIELD)
            else [MODERN_MULTI_EXPENSE_FIELD],
            as_dict=True,
        )

        if not payment_entry:
            continue

        if not payment_entry.get(MODERN_MULTI_EXPENSE_FIELD):
            values[MODERN_MULTI_EXPENSE_FIELD] = 1

        if frappe.db.has_column("Payment Entry", MODERN_TOTAL_AMOUNT_FIELD) and not frappe.utils.flt(
            payment_entry.get(MODERN_TOTAL_AMOUNT_FIELD)
        ):
            values[MODERN_TOTAL_AMOUNT_FIELD] = frappe.utils.flt(row.total_amount)

        if values:
            frappe.db.set_value("Payment Entry", row.parent, values, update_modified=False)
            updated += 1

    return updated


def has_payment_entry_field(fieldname: str) -> bool:
    return frappe.get_meta("Payment Entry").has_field(fieldname)
