"""
ERPNext Payment Entry override for cheque status filtering.

This module monkey-patches ERPNext's get_advance_payment_entries function
to exclude payments with problematic cheque statuses (Returned, Rejected,
Return To Holder) while preserving non-cheque payments (NULL cheque_status).

The override is conditionally applied based on:
- App installation status
- cheque_status field existence in Payment Entry
- Per-company enable_optima_payment flag

Applied in: optima_payment/__init__.py
Original function: erpnext.controllers.accounts_controller.get_advance_payment_entries
"""

import frappe
from erpnext.controllers.accounts_controller import get_common_query
from erpnext.controllers.accounts_controller import get_advance_payment_entries

# Store original function
original_get_advance_payment_entries = get_advance_payment_entries

# Module-level variable to cache the check result
_use_optima_cache = {}

def clear_optima_cache(site_name: str = None) -> None:
    """Clear optima implementation cache for specific site or all sites."""
    global _use_optima_cache
    if site_name:
        _use_optima_cache.pop(site_name, None)
    else:
        _use_optima_cache.clear()


def should_use_optima_implementation() -> bool:
    """
    Check if Optima Payment override should be active.

    Returns True only if:
    - App installed and DocType accessible
    - cheque_status field exists in Payment Entry
    - At least one company has enable_optima_payment=1

    Checking per-company enable flag prevents site-wide activation.
    """
    if "optima_payment" not in frappe.get_installed_apps():
        return False

    if not frappe.db.exists("DocType", "Optima Payment Setting"):
        return False

    try:
        if not frappe.db.has_column("Payment Entry", "cheque_status"):
            return False
    except Exception:
        try:
            frappe.db.sql("SELECT cheque_status FROM `tabPayment Entry` LIMIT 1", as_dict=True)
        except Exception:
            return False

    enabled_count = frappe.db.count(
        "Optima Payment Setting",
        filters={"enable_optima_payment": 1}
    )

    return enabled_count > 0


def optima_get_advance_payment_entries(*args, **kwargs):
    """Route to Optima or ERPNext implementation based on per-site cached check."""
    try:
        site_name = frappe.local.site

        if site_name not in _use_optima_cache:
            _use_optima_cache[site_name] = should_use_optima_implementation()

        if _use_optima_cache[site_name]:
            return _optima_get_advance_payment_entries(*args, **kwargs)
        else:
            return original_get_advance_payment_entries(*args, **kwargs)

    except Exception as e:
        frappe.logger().error(f"Error in optima wrapper: {str(e)}")
        return original_get_advance_payment_entries(*args, **kwargs)


def _optima_get_advance_payment_entries(
	party_type,
	party,
	party_account,
	order_doctype,
	order_list=None,
    default_advance_account=None,
	include_unallocated=True,
	against_all_orders=False,
	limit=None,
	condition=None,
):
	"""
	Fetch advance payment entries with cheque_status filtering.

	Extends ERPNext's get_advance_payment_entries to exclude payments
	with problematic cheque statuses (Returned, Rejected, Return To Holder)
	while preserving non-cheque payments (NULL cheque_status).
	"""
	payment_entries = []
	payment_entry = frappe.qb.DocType("Payment Entry")

	if order_list or against_all_orders:
		q = get_common_query(
			party_type,
			party,
			party_account,
            default_advance_account,
			limit,
			condition,
		)
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = q.inner_join(payment_ref).on(payment_entry.name == payment_ref.parent)
		q = q.select(
			(payment_ref.allocated_amount).as_("amount"),
			(payment_ref.name).as_("reference_row"),
			(payment_ref.reference_name).as_("against_order"),
            (payment_entry.book_advance_payments_in_separate_party_account),
		)

		q = q.where(payment_ref.reference_doctype == order_doctype)
		if order_list:
			q = q.where(payment_ref.reference_name.isin(order_list))

		allocated = list(q.run(as_dict=True))
		payment_entries += allocated

	if include_unallocated:
		q = get_common_query(
			party_type,
			party,
			party_account,
            default_advance_account,
			limit,
			condition,
		)
		q = q.select((payment_entry.unallocated_amount).as_("amount"))
		q = q.where(payment_entry.unallocated_amount > 0)

		# Exclude problematic cheque statuses but include NULL (non-cheque payments).
		q = q.where(
			(payment_entry.cheque_status.isnull()) |
			(payment_entry.cheque_status == '') |
			(~payment_entry.cheque_status.isin(['Returned', 'Rejected', 'Return To Holder']))
		)

		unallocated = list(q.run(as_dict=True))
		payment_entries += unallocated

	return payment_entries
