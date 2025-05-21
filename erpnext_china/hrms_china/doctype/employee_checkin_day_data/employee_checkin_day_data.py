# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeCheckinDayData(Document):
	
	def calculate_checkin_result(self):
		code = frappe.db.get_value("Employee Checkin Group", 
			filters={"group_name": self.group_name, "group_id": self.group_id}, fieldname="code")
		if code:
			exec(code, globals())
			func = globals()['func']
			self.result = func(self.raw)

	def before_save(self):
		self.calculate_checkin_result()

