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

	def set_values(self):
		if self.raw:
			sp_items = self.raw.get('sp_items', [])
			for item in sp_items:
				if int(item.get('count', 0)) > 0:
					self.sp_type = item.get("name")
					duration = item.get("duration")
					if item.get("time_type") == 0:
						# 天
						self.sp_time_type = "天"
						self.sp_duration = int(duration) / 86400
					else:
						# 小时
						self.sp_time_type = "小时"
						self.sp_duration = int(duration) / 3600
					break
	
	def before_save(self):
		self.calculate_checkin_result()
		self.set_values()

