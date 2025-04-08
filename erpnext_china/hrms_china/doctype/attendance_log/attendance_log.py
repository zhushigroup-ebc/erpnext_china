# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months, add_days
from frappe.model.document import Document


class AttendanceLog(Document):
	def validate(self):
		month_start = add_days(add_months(self.attendance_date,-1),1)
		month_end = add_days(add_months(self.attendance_date,1),-1)
		attendance_log =  frappe.db.exists("Attendance Log", 
			{
				"employee": self.employee,
				"attendance_date": ['between',[month_start, month_end]],
				"docstatus":1,
				"name":['!=',self.name]
			}
		)
		if attendance_log:
			frappe.throw("已经存在该员工在当月的考勤记录{0},跳过新建记录".format(attendance_log))
