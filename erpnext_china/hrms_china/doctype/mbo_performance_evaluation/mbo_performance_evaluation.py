# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document


class MBOPerformanceEvaluation(Document):

	def add_workflow_state_record(self):
		if self.has_value_changed("workflow_state"):
			employee = ""
			emp_name = ""
			if frappe.session.user == "Administrator":
				emp_name = "Administrator"
			else:
				emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "first_name"], as_dict=True)
				if emp:
					employee = emp.name
					emp_name = emp.first_name
			
			self.append("workflow_records", {
				"workflow_state": self.workflow_state,
				"employee": employee,
				"employee_name": emp_name,
				"approval_date": frappe.utils.now()
			})

	def set_missing_value(self):
		if not (self.employee and self.department and self.designation):
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "department", "designation"], as_dict=True)
			self.department = employee.department
			self.employee = employee.name
			self.designation = employee.designation

	def before_save(self):
		self.set_missing_value()
		self.add_workflow_state_record()