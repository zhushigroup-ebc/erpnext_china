# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document


class MBOPerformanceEvaluation(Document):

	def set_missing_value(self):
		if not (self.employee and self.department and self.designation):
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "department", "designation"], as_dict=True)
			if employee:
				self.department = employee.department
				self.employee = employee.name
				self.designation = employee.designation

	def validate_score(self):
		total_score = 0
		final_score = 0
		for item in self.performance_evaluation_and_summary_form:
			total_score = total_score + (item.weighting or 0)
			final_score = final_score + (item.score or 0)
		self.total_score = total_score
		self.final_score = final_score

	def before_save(self):
		self.set_missing_value()
		self.validate_score()


@frappe.whitelist()
def get_workflow_action(doc_name):
	query = f'''
		SELECT
			wa.workflow_state, wa.modified, u.first_name, wa.status
		FROM
			`tabWorkflow Action` AS wa
			LEFT JOIN `tabUser` AS u ON wa.completed_by = u.`name` 
		WHERE
			wa.reference_name = "{doc_name}" 
			AND wa.reference_doctype = "MBO Performance Evaluation" 
		ORDER BY wa.creation DESC
	'''
	workflow_actions = frappe.db.sql(query, as_dict=1)
	return {"actions": workflow_actions}
