# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

from operator import itemgetter
from itertools import groupby
from datetime import datetime

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data

def get_data(filters: dict):
	sql = get_conditions(filters)
	rows = frappe.db.sql(sql, as_dict=True)
	rows.sort(key=itemgetter('date', 'department', 'employee', 'result'))
	final_result = []
	for (date, department, employee, result), items in groupby(rows, key=itemgetter('date', 'department', 'employee', 'result')):
		row_header_data = {
			'date': date,
			'department': department,
			'employee': employee,
			'result': result,
		}
		final_result.append(row_header_data)
		for item in items:
			item['date'] = None
			item['department'] = None
			item['employee'] = None
			item['result'] = None
			final_result.append(item)

	return final_result

def get_conditions(filters):

	conditions = []
	year = filters.get('year', datetime.now().year)
	month = filters.get('month', datetime.now().month)
	conditions.append(f"YEAR ( ecdd.`date` ) = {year} AND MONTH(ecdd.`date`) = {month}")
	if filters.get('department'):
		department = frappe.db.escape(filters['department'])
		conditions.append(f"ecdd.department = {department}")
	if filters.get('employee'):
		employee = frappe.db.escape(filters['employee'])
		conditions.append(f"ecdd.employee = {employee}")
	if filters.get('result'):
		result = frappe.db.escape(filters['result'])
		conditions.append(f"ecdd.result = {result}")
	
	sql = f"""
		SELECT 
			ecdd.`date`, 
			ecdd.employee_name as employee, 
			ecdd.department,
			ecdd.result, 
			ecl.checkin_time, 
			ecl.checkin_type, 
			ecl.result as checkin_result,
			1 as indent
		FROM `tabEmployee Checkin Day Data` as ecdd 
		RIGHT JOIN `tabEmployee Checkin Log` as ecl 
		ON ecdd.acctid = ecl.user_id AND DATE(ecdd.`date`)=DATE(ecl.checkin_time) 
		WHERE {" AND ".join(conditions)} ORDER BY ecl.checkin_time	
		"""
	return sql


def get_columns(filters):
	columns = [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Data",
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
		},
		{
			"label": _("Result"),
			"fieldname": "result",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Checkin Type"),
			'fieldname': 'checkin_type',
			'fieldtype': 'Data',
		},
		{
			"label": _("Checkin Time"),
			"fieldname": "checkin_time",
			"fieldtype": "Datetime",
			"width": 200,
		},
		{
			'label': _("Checkin Result"),
			'fieldname': 'checkin_result',
			'fieldtype': 'Data',
		}
	]
	
	return columns