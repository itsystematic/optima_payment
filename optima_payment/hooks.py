app_name = "optima_payment"
app_title = "Optima Payment"
app_publisher = "IT Systematic"
app_description = "App For Cheque Status"
required_apps = [
    "erpnext",
    "frappe"
]
app_email = "sales@itsystematic.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "optima_payment",
# 		"logo": "/assets/optima_payment/logo.png",
# 		"title": "Optima Payment",
# 		"route": "/optima_payment",
# 		"has_permission": "optima_payment.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/optima_payment/css/optima_payment.css"
app_include_js = [
    "/assets/optima_payment/js/optima_payment.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/optima_payment/css/optima_payment.css"
# web_include_js = "/assets/optima_payment/js/optima_payment.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "optima_payment/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
page_js = {"print" : "public/js/print_view.js"}

# include js in doctype views
doctype_js = {
    "Payment Entry" : [
        "public/js/payment_entry.js" ,
        "public/js/controllink.js" ,
        "public/js/form.js"
    ],
    "Expense Claim": "public/js/expense_claim.js",
    "Expense Claim Type" : "public/js/expense_claim_type.js",
    "Bank": "public/js/bank.js", #--WS
    "Bank Guarantee" : "public/js/bank_guarantee.js"
}
doctype_list_js = {
    "Payment Entry" : "public/js/payment_entry_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "optima_payment/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": "optima_payment.cheque.utils.money_to_words",
	# "filters": "optima_payment.utils.jinja_filters"
}

# Installation
# ------------

# before_install = "optima_payment.install.before_install"
# after_install = "optima_payment.install.after_install"

after_migrate = "optima_payment.migrate.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "optima_payment.uninstall.before_uninstall"
# after_uninstall = "optima_payment.uninstall.after_uninstall"

boot_session = "optima_payment.startup.boot.add_optima_payment_setting"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "optima_payment.utils.before_app_install"
after_app_install = "optima_payment.install.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "optima_payment.utils.before_app_uninstall"
after_app_uninstall = "optima_payment.uninstall.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "optima_payment.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
override_doctype_class = {
	"Expense Claim": "optima_payment.override.doctype_class.expense_claim.CustomExpenseClaim", # --AM
    "Payment Entry": "optima_payment.override.doctype_class.payment_entry.CustomPaymentEntry", # --FH
    "Bank Guarantee": "optima_payment.override.doctype_class.bank_guarantee.CustomBankGuarantee",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Payment Entry": {
        "on_submit" : "optima_payment.doc_events.payment_entry.payment_entry_on_submit" ,
        "on_cancel" : "optima_payment.doc_events.payment_entry.payment_entry_on_cancel" ,
        "on_trash" : "optima_payment.doc_events.payment_entry.payment_entry_on_trash" ,
	},
    "Journal Entry" :{
        "on_cancel" :  "optima_payment.doc_events.journal_entry.journal_entry_on_cancel",
    },
    # "Expense Claim" : {
        # "on_submit" : "optima_payment.doc_events.expense_claim.on_submit",
        # "on_cancel" : "optima_payment.doc_events.expense_claim.on_cancel",
        # "validate" : "optima_payment.doc_events.expense_claim.validate"
    # }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"optima_payment.tasks.daily.optima_payment_daily"
	]
}

# Testing
# -------

# before_tests = "optima_payment.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "optima_payment.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "optima_payment.task.get_dashboard_data"
# }
override_doctype_dashboards = {
	"Purchase Invoice": "optima_payment.override.dashboard.purchase_invoice.get_data"
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["Cheque Action Log"]

# Request Events
# ----------------
# before_request = ["optima_payment.utils.before_request"]
# after_request = ["optima_payment.utils.after_request"]

# Job Events
# ----------
# before_job = ["optima_payment.utils.before_job"]
# after_job = ["optima_payment.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"optima_payment.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "dt" : "Role" ,
        "filters" : [
            ["name", "in", ["Optima Payment User", "Optima Payment Manger"]]
        ]
    },
    {
        "dt" : "Custom DocPerm" ,
        "filters" : [
            ["role", "in", ["Optima Payment User", "Optima Payment Manger"]]
        ]
    }

    # {
    #     "dt": "Print Format",
    #     "filters": {
    #         "doc_type": "Payment Entry",
    #         "name": "Payment Entry",
    #         # "property": "links_order",
    #     }
    # },
    # {
    #     "dt": "Workspace",
    #     "filters": [
    #         ["name", "in", ["Accounting", "ERPNext Settings", "Financial Reports"]] 
    #     ]
    # }
]