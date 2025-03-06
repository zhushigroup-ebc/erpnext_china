# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from collections import Counter
import frappe
from erpnext.setup.doctype.employee.employee import *
from datetime import datetime
import json
from pathlib import Path
import pandas as pd

class CustomEmployee(Employee):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Active", "Inactive", "Suspended", "Left"])

		self.employee = self.name
		self.set_employee_name()
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.validate_preferred_email()
		self.validate_unique_salary_component_item()

		#定制
		self.set_gender()
		self.set_date_of_birth()
		self.set_city_of_birth()
		self.set_degree()
		self.set_two_social_insurance()
		self.set_three_social_insurance()
		self.set_housing_provident_fund()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				remove_user_permission("Employee", self.name, existing_user_id)

	@property
	def custom_age(self):
		id_card = self.custom_chinese_id_number
		if id_card:
			days = datetime.now()-datetime.strptime(f'{id_card[6:10]}-{id_card[10:12]}-{id_card[12:14]}','%Y-%m-%d')
			return  int(days.days/365)

	def set_degree(self):
		d = ['博士研究生','硕士研究生','本科','大专','高中(中专)']
		m = 999
		try:
			for i in self.education:
				m = min(d.index(i.level),m)
			self.custom_degree = d[m]
		except:
			pass
			
	def set_date_of_birth(self):
		id_card = self.custom_chinese_id_number
		try:
			self.date_of_birth = f'{id_card[6:10]}-{id_card[10:12]}-{id_card[12:14]}'
		except:
			pass

	def set_gender(self):
		id_card = self.custom_chinese_id_number
		if id_card:
			gender_id = int(self.custom_chinese_id_number[-2])%2
			if gender_id == 1:
				self.gender = 'Male'
			else:
				self.gender = 'Female'


	def set_city_of_birth(self):
		id_card = self.custom_chinese_id_number
		if id_card:
			with open((Path(__file__).parent / 'china_city_code.json'),'rb') as file:
				china_city_code_json = file.read()
			china_city_code_dict = json.loads(china_city_code_json)
			self.custom_city_of_birth = china_city_code_dict[id_card[:6]]

	def set_two_social_insurance(self):
		if not self.custom_two_social_insurance:
			self.custom_two_social_insurance_pay_type = None
			self.custom_two_social_insurance_base_rate = 0
			
	def set_three_social_insurance(self):
		if not self.custom_three_social_insurance:
			self.custom_three_social_insurance_pay_type = None
			self.custom_three_social_insurance_base_rate = 0
			self.custom_social_security_payment_company = None
	
	def set_housing_provident_fund(self):
		if not self.custom_housing_provident_fund:
			self.custom_housing_provident_fund_pay_type = None
			self.custom_housing_provident_fund_base_rate = 0

	def has_duplicates(self):
		return any(count > 1 for count in Counter([i.salary_component for i in self.custom_salary_components_items]).values())

	def validate_unique_salary_component_item(self):
		if self.has_duplicates():
			frappe.throw('薪资构成项不可重复！')

@frappe.whitelist()
def get_employee_tree(parent, 
					pluck = 'email',
					orient = 'list',
					levle = None,
					is_root = None,
					use_cache = False,
					has_parent = False):
	'''
	注意：io压力增加时进一步优化缓存缓存内容

	parent: default None
		用户唯一标识的类型，可以输入str或dict
		key: email|userid|username
		value: 唯一标识的值

	pluck: default 'email' 返回的字段名
		email|userid|username

	orient: list|dict , 是否返回树状结构

	levle: all|int ,返回多少层级的信息

	is_root: False
	'''
	users = []
	if is_root:
		# 树的最顶点
		employee = 'zhukunfu@zhushigroup.cn'
	
	df = pd.DataFrame(json.loads(frappe.cache.get('hrms_employee_children')))
	reports_to_user_columns = ['reports_to_user_5','reports_to_user_4','reports_to_user_3','reports_to_user_2','reports_to_user']
	for col in reports_to_user_columns:
		if sum(df[col]==parent)>0:
			users = df.user_id[(df[col]==parent)&(~df['user_id'].isna())].drop_duplicates().to_list()
			break	
	return users


def scheduled_tasks_employee_children():
    import frappe,datetime
    cache = frappe.cache()
    import pandas as pd
    import numpy as np
    def run():
        column_name = ['modified','name', 'employee', 'employee_name', 'gender', 'date_of_birth','date_of_joining', 'status', 'user_id', 'reports_to']
        data = frappe.db.get_all('Employee',fields = column_name,as_list=True)
        df = pd.DataFrame(data,columns=column_name)

        df.replace('[NULL]',np.nan,inplace=True)
        reports_to_dict = dict(zip(df.name.to_list(),df.reports_to.to_list()))
        emp_for_user_dict = dict(zip(df.name.to_list(),df.user_id.to_list()))

        df['reports_to'] = df.reports_to.fillna(df.name)

        df['reports_to_2'] = df.reports_to.map(reports_to_dict)
        df['reports_to_2'] = df.reports_to_2.fillna(df.reports_to)

        df['reports_to_3'] = df.reports_to_2.map(reports_to_dict)
        df['reports_to_3'] = df.reports_to_3.fillna(df.reports_to_2)

        df['reports_to_4'] = df.reports_to_3.map(reports_to_dict)
        df['reports_to_4'] = df.reports_to_4.fillna(df.reports_to_3)

        df['reports_to_5'] = df.reports_to_4.map(reports_to_dict)
        df['reports_to_5'] = df.reports_to_5.fillna(df.reports_to_4)

        df['reports_to_user'] = df.reports_to.map(emp_for_user_dict)
        df['reports_to_user_2'] = df.reports_to_2.map(emp_for_user_dict)
        df['reports_to_user_3'] = df.reports_to_3.map(emp_for_user_dict)
        df['reports_to_user_4'] = df.reports_to_4.map(emp_for_user_dict)
        df['reports_to_user_5'] = df.reports_to_5.map(emp_for_user_dict)

        cache.set('hrms_employee_children', df.to_json())

    if frappe.cache.get('hrms_employee_children') != None:
        last_dt=frappe.db.get_all('Employee',fields = ['max(modified) as max_dt'],as_list=True)[0][0]
        df = pd.DataFrame(json.loads(frappe.cache.get('hrms_employee_children')))
        cache_dt = datetime.datetime.fromtimestamp(df.modified.max()/1000)
        dt_diff = (last_dt - cache_dt)
        if dt_diff.seconds <20:
            return 
    run()