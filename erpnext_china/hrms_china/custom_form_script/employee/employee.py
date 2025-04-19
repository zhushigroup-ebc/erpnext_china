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
def scheduled_tasks_employee_children():
    import frappe,datetime
    cache = frappe.cache()
    import pandas as pd
    import numpy as np
    
    column_name = ['modified','name', 'employee', 'employee_name', 'gender', 'date_of_birth','date_of_joining', 'status', 'user_id', 'reports_to']
    data = frappe.db.get_all('Employee',fields = column_name,as_list=True)
    df = pd.DataFrame(data,columns=column_name)

    df.replace('[NULL]',np.nan,inplace=True)
    df['reports_to'] = df.reports_to.fillna(df.name)
    reports_to_dict = dict(zip(df.name.to_list(),df.reports_to.to_list()))
    emp_for_user_dict = dict(zip(df.name.to_list(),df.user_id.to_list()))


    df['reports_to_2'] = df.reports_to.map(reports_to_dict)
    df['reports_to_3'] = df.reports_to_2.map(reports_to_dict)
    df['reports_to_4'] = df.reports_to_3.map(reports_to_dict)
    df['reports_to_5'] = df.reports_to_4.map(reports_to_dict)

    def fix_user_id(arr):
        data = [arr.reports_to,arr.reports_to_2,arr.reports_to_3,arr.reports_to_4,arr.reports_to_5,arr.reports_to_5]
        for i in list(range(1,4)):
            if data[i] == data[i+1]:
                data[i] = data[i-1]
            else:
                pass
        return pd.Series(data[1:-2], index=['reports_to_2','reports_to_3','reports_to_4'] )
    df[['reports_to_2','reports_to_3','reports_to_4']] = df.apply(fix_user_id,axis=1)
    df['reports_to_user'] = df.reports_to.map(emp_for_user_dict)
    df['reports_to_user_2'] = df.reports_to_2.map(emp_for_user_dict)
    df['reports_to_user_3'] = df.reports_to_3.map(emp_for_user_dict)
    df['reports_to_user_4'] = df.reports_to_4.map(emp_for_user_dict)
    df['reports_to_user_5'] = df.reports_to_5.map(emp_for_user_dict)

    report_to_user_list = df.reports_to_user.dropna().drop_duplicates().to_list()
    for user_id in report_to_user_list:
        users = df.user_id[((df['reports_to_user']==user_id)|(df['reports_to_user_2']==user_id)|(df['reports_to_user_3']==user_id)|(df['reports_to_user_4']==user_id)|(df['reports_to_user_5']==user_id))&(~df['user_id'].isna())].drop_duplicates().to_list()
        cache.set(f'hrms_employee_children_{user_id}', json.dumps(users))
    for user_id in report_to_user_list:
        users = df.name[((df['reports_to_user']==user_id)|(df['reports_to_user_2']==user_id)|(df['reports_to_user_3']==user_id)|(df['reports_to_user_4']==user_id)|(df['reports_to_user_5']==user_id))&(~df['user_id'].isna())].drop_duplicates().to_list()
        cache.set(f'hrms_employee_children_emp_{user_id}', json.dumps(users))
    
    cache.set('hrms_employee_children', df.to_json())
    for user_id in df.user_id.dropna().drop_duplicates().to_list():
        parents = df[df.user_id==user_id][['user_id','reports_to_user','reports_to_user_2','reports_to_user_3','reports_to_user_4','reports_to_user_5']].iloc[0].dropna().drop_duplicates().to_list()
        parents = str(tuple(parents)).replace(',)',')')
        cache.set(f'hrms_employee_parent_str_{user_id}', parents)

@frappe.whitelist()
def get_employee_tree(parent, 
                    pluck = 'userid',
                    has_parent = False,
                    orient = 'list',
                    levle = None,
                    is_root = None,
                    use_cache = False):
    '''
    注意：io压力增加时进一步优化缓存缓存内容

    parent: default None
        用户唯一标识的类型，可以输入str或dict
        key: email|userid|username
        value: 唯一标识的值

    pluck: userid|employee
    has_parent True|False
    orient: list|dict , 是否返回树状结构

    levle: all|int ,返回多少层级的信息

    is_root: False
    '''
    users = []
    cache_path = {'userid':'hrms_employee_children',
                'employee':'hrms_employee_children_emp'}

    try:
        users = json.loads(frappe.cache.get(f'{ cache_path[pluck] }_{ parent }'))
        if has_parent:
            if pluck == 'userid':
                users.append(user)
            elif pluck == 'employee':
                emp_json = json.loads(frappe.cache.get(f'hrms_employee_children'))
                df = pd.DataFrame(emp_json)
                emp = df.name[df.user_id==user].iloc[0]
                users.append(emp)
            else:
                pass
    except:
        pass
    return users
