# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeCheckinLog(Document):
	def calculate_checkin_result(self):
		settings = frappe.get_single("Employee Checkin Settings")
		if settings and settings.checkin_log_func:
			exec(settings.checkin_log_func, globals())
			func = globals()['func']
			self.result = func(self.raw)
	
	def before_save(self):
		self.calculate_checkin_result()
