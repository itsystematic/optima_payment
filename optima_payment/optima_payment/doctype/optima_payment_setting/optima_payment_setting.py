# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe , json
from frappe.model.document import Document
from frappe import get_app_path

class OptimaPaymentSetting(Document):
	

	def before_save(self) :
		self.enable_print_format()


	def enable_print_format(self):
		print_format_names = get_print_format_names()
		frappe.db.sql("""
				UPDATE `tabPrint Format` SET disabled = {0}  WHERE name IN {1}
		""".format(
				not self.enable_optima_payment , tuple(print_format_names)
			), auto_commit=True)




def get_print_format_names() :

	app_path = get_app_path("optima_payment" , "files" , "print_format.json")
	
	with open(app_path , "r") as file :
		file_data = json.load(file)

	return list(map(lambda x : x.get("name") , file_data))