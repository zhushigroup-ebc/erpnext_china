# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import pandas as pd
import numpy as np
from frappe.utils import add_days, get_datetime, flt, get_date_str


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data


def get_data(filters):
	res = get_salary_components(filters)
	df = pd.DataFrame.from_records(res)
	get_attendance_data(filters,df)
	salary_component_calculation(df)
	data = group_data(df)
	income_tax_calculation(df)
	data.fillna(0, inplace=True)
	return data.to_dict(orient='records')

def income_tax_calculation(df):
	pass

def get_columns(filters):
	columns = [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},]
	if filters.get('show_details'):
		columns.extend([
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Date of Joining"),
			"fieldname": "date_of_joining",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 240,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 240,
		},])
	columns.extend([
		{
			"label": _("Expected Attendance Days"),
			"fieldname": "expected_attendance_days",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Attendance Days"),
			"fieldname": "attendance_days",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Attendance Rate"),
			"fieldname": "attendance_rate",
			"fieldtype": "Percent",
			"width": 120,
		},
	])

	sc = frappe.get_all('Salary Component',order_by='type desc,creation',pluck="name")
	for d in sc:
		columns.append({
			"label": d,
			"fieldname": d,
			"fieldtype": "Currency",
			"width": 120,
		})

	columns.extend([
		{
			"label": _("Total Income"),
			"fieldname": "total_income",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Total Deduction"),
			"fieldname": "total_deduction",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Total Taxable Income"),
			"fieldname": "total_taxable_income",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Total Taxable Deduction"),
			"fieldname": "total_taxable_deduction",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Net Taxable Income"),
			"fieldname": "net_taxable_income",
			"fieldtype": "Currency",
			"width": 120,
		},
	])
	return columns

def get_conditions(filters,for_employee=None):
	(start, end) = get_date(filters)
	conditions = ""
	if for_employee:
		# attendance log query
		conditions = " and al.attendance_date between '{}' and '{}'".format(start, end)
	if filters.get('employee'):
		conditions += " and e.name = '%s'" % filters.get('employee')
	if filters.get('department'):
		conditions += " and e.department = '%s'" % filters.get('department')
	if filters.get('company'):
		conditions += " and e.company = '%s'" % filters.get('company')
	return conditions


def get_date(filters):
	if not filters.get('to_date'):
		frappe.throw(_('{0} is required').format(_('To Date')))
	start = get_datetime(filters.get('to_date')).replace(day=1)
	current_month = get_datetime(filters.get('to_date')).month
	if current_month == 12:
		next_month = 1
	else:
		next_month = current_month + 1
	
	end = add_days(get_datetime(filters.get('to_date')).replace(day=1,month=next_month),-1)
	return get_date_str(start), get_date_str(end)

def get_salary_components(filters):
	conditions = get_conditions(filters)
	salary_query = f"""
		select
			e.name as employee,
			e.employee_name,
			e.date_of_joining,
			e.department,
			e.custom_social_security_payment_company as company,
			es.amount,
			sc.name as salary_component,
			case when sc.description like 'def %' then sc.description end as description,
			sc.type,
			sc.is_tax_applicable
		from
			`tabEmployee` as e
		left join
			`tabEmployee Salary Component` as es on es.parent = e.employee
		left join
			`tabSalary Component` sc on sc.name = es.salary_component
		where
			e.date_of_joining < '{filters.get('to_date')}'
			and e.status = 'Active'
			{conditions}
		order by
			e.name, es.idx
	"""

	return frappe.db.sql(salary_query, as_dict=1)

def calculate_personal_income_tax(df):
	
	return

def get_attendance_data(filters,df):
	conditions = get_conditions(filters,for_employee=True)
	att_query = f"""
		select
			e.name as employee,
			al.expected_attendance_days,
			al.attendance_days
		from
			`tabAttendance Log` al, `tabEmployee` e
		where
			al.docstatus = 1
			and al.employee = e.name
			{conditions}
	"""
	att = frappe.db.sql(att_query, as_dict=1,debug=frappe.get_conf().developer_mode)

	att_dict = {record['employee']: record for record in att}
	for index, row in df.iterrows():
		attendance_rate = 0
		if att_dict.get(row['employee']):
			employee_record = att_dict[row['employee']]
			if employee_record.get('expected_attendance_days'):
				attendance_rate = round(employee_record['attendance_days'] / employee_record['expected_attendance_days'], 3) * 100
		df.at[index, 'attendance_rate'] = attendance_rate
		df.at[index, 'expected_attendance_days'] = att_dict.get(row['employee'], {}).get('expected_attendance_days', 0)
		df.at[index, 'attendance_days'] = att_dict.get(row['employee'], {}).get('attendance_days', 0)
	
def salary_component_calculation(df):
	def execute_dynamic_function(row):
		if not row['description'] or not row['description'].strip():
			return row['amount']
		local_namespace = {}
		try:
			exec(row['description'], {}, local_namespace)
		except Exception as e:
			frappe.log_error(e)
			return row['amount']
		
		scc_func = local_namespace.get('salary_component_calculation')
		
		if callable(scc_func):
			return scc_func(row)
		else:
			frappe.log_error("Failed to create the salary component calculation function")
			return row['amount']

	df['amount'] = df.apply(execute_dynamic_function, axis=1)

def group_data(df):
	df[['company','department']] = df[['company','department']].fillna(_('Unknown'))
	df.fillna(0, inplace=True)
	cols = ['employee','employee_name','date_of_joining','company','department','expected_attendance_days','attendance_days','attendance_rate']
	pivot_df = df.pivot_table(index=cols, columns='salary_component', values='amount', aggfunc='sum', fill_value=0).reset_index()

	deduct_summary = df[df['type'] == '扣除'].groupby('employee')['amount'].sum().reset_index(name='total_deduction')
	income_summary = df[df['type'] == '收入'].groupby('employee')['amount'].sum().reset_index(name='total_income')
	taxable_income_summary = df[(df['type'] == '收入') & (df['is_tax_applicable'] == 1)].groupby('employee')['amount'].sum().reset_index(name='total_taxable_income')
	taxable_deduct_summary = df[(df['type'] == '扣除') & (df['is_tax_applicable'] == 1)].groupby('employee')['amount'].sum().reset_index(name='total_taxable_deduction')

	pivot_df = pivot_df.merge(deduct_summary, on='employee', how='left')
	pivot_df = pivot_df.merge(income_summary, on='employee', how='left')
	pivot_df = pivot_df.merge(taxable_income_summary, on='employee', how='left')
	pivot_df = pivot_df.merge(taxable_deduct_summary, on='employee', how='left')

	pivot_df['net_taxable_income'] = np.where(
        (pivot_df['total_taxable_income'] - pivot_df['total_taxable_deduction'] - 5000) < 0,
        0,
        pivot_df['total_taxable_income'] - pivot_df['total_taxable_deduction'] - 5000
    )
	return pivot_df

@frappe.whitelist()
def get_salary_components_list():
	# used to avoid insufficient role permissions in formatter
	query = f"""
		select
			name as salary_component,
			type,
			is_tax_applicable
		from
			`tabSalary Component`
	"""
	
	return frappe.db.sql(query,as_dict=1)
