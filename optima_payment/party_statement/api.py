# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Entry points for the statement of account: the two reports and the preview page."""

import frappe
from frappe import _
from frappe.utils import formatdate
from frappe.utils.xlsxutils import make_xlsx

from optima_payment.party_statement.statement import (
    REPORTS,
    excel_rows,
    file_name,
    get_statement,
    render_html,
    render_pdf,
    report_columns,
    report_message,
    report_rows,
    report_summary,
    validate_party_type,
)


def check_access(party_type: str, party: str | None) -> None:
    """A statement is for whoever can read the party and open its statement report."""
    validate_party_type(party_type)
    frappe.has_permission(party_type, "read", party, throw=True)

    report = REPORTS[party_type]
    if not frappe.get_doc("Report", report).is_permitted():
        frappe.throw(_("You are not permitted to open the {0} report.").format(_(report)), frappe.PermissionError)


def run_report(party_type: str, filters: dict | None) -> tuple:
    """execute() of the Customer Statement and Supplier Statement reports."""
    filters = frappe._dict(filters or {})
    check_access(party_type, filters.party)

    statement, header = get_statement(party_type, filters.party, filters.company, filters.from_date, filters.to_date)
    return (
        report_columns(header.currency),
        report_rows(statement, header),
        report_message(statement, header),
        None,
        report_summary(statement, header),
    )


@frappe.whitelist()
def get_preview_html(party_type: str, party: str, company: str, from_date: str, to_date: str) -> str:
    check_access(party_type, party)
    return render_html(*get_statement(party_type, party, company, from_date, to_date))


@frappe.whitelist()
def download_pdf(party_type: str, party: str, company: str, from_date: str, to_date: str) -> None:
    check_access(party_type, party)
    pdf = render_pdf(*get_statement(party_type, party, company, from_date, to_date))
    send_file(file_name(party, to_date, "pdf"), pdf)


@frappe.whitelist()
def download_excel(party_type: str, party: str, company: str, from_date: str, to_date: str) -> None:
    check_access(party_type, party)
    rows = excel_rows(*get_statement(party_type, party, company, from_date, to_date))
    send_file(file_name(party, to_date, "xlsx"), make_xlsx(rows, _("Statement of Account")).getvalue())


@frappe.whitelist(methods=["POST"])
def make_email_attachment(party_type: str, party: str, company: str, from_date: str, to_date: str) -> dict:
    """The statement's PDF as a private File, with the party's email and a subject for the composer."""
    check_access(party_type, party)
    statement, header = get_statement(party_type, party, company, from_date, to_date)

    attachment = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name(party, to_date, "pdf"),
            "content": render_pdf(statement, header),
            "is_private": 1,
            "folder": "Home/Attachments",
        }
    ).insert()

    return {
        "file": {"name": attachment.name, "file_name": attachment.file_name, "file_url": attachment.file_url},
        "recipients": frappe.db.get_value(party_type, party, "email_id"),
        "subject": _("Statement of Account for {0}, {1} to {2}").format(
            header.party_name, formatdate(header.from_date), formatdate(header.to_date)
        ),
    }


def send_file(name: str, content: bytes) -> None:
    frappe.local.response.filename = name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
