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
def scheduled_tasks_employee_children():
    import frappe,datetime
    cache = frappe.cache()
    import pandas as pd
    import numpy as np

    data = frappe.db.sql('''select name as emp1 from ebc.tabEmployee
    where ebc.tabEmployee.status = 'Active'
    and ebc.tabEmployee.reports_to is null''',as_dict=0)
    df_ = pd.DataFrame(data,columns=['emp1'])

    column_name = column_name = ['name','first_name','user_id','reports_to']
    data = frappe.db.get_all('Employee',fields = column_name,as_list=True)
    df = pd.DataFrame(data=data,columns=column_name)
    df.replace('[NULL]',np.nan,inplace=True)
    def get_children(employee):
        return df[df.reports_to == employee].name.to_list()
    def get_userid(employee):
        try:
            return df[df.name == employee].user_id.iloc[0]
        except:
            return None
    def get_empname(employee):
        try:
            return df[df.name == employee].first_name.iloc[0]
        except:
            return None

    df_['user_id1'] = df_['emp1'].apply(get_userid)
    df_['name1'] = df_['emp1'].apply(get_empname)
    for i in list(range(1,6)):
        df_['emp'+str(i+1)] = df_['emp'+str(i)].apply(get_children)
        df_ = df_.explode('emp'+str(i+1))
        
        df_['user_id'+str(i+1)] = df_['emp'+str(i+1)].apply(get_userid)
        df_['name'+str(i+1)] = df_['emp'+str(i+1)].apply(get_empname)

    df_ = df_.sort_index(axis=1)
    report_to_list = df[~df['user_id'].isna()].reports_to.dropna().drop_duplicates().to_list()
    for emp in report_to_list:
        users_df = df_[(df_['emp1']==emp)|(df_['emp2']==emp)|(df_['emp3']==emp)|(df_['emp4']==emp)|(df_['emp6']==emp)]
        users = []
        for i in list(range(1,6)):
            users = users + users_df['user_id'+str(i)].dropna().drop_duplicates().to_list()
        user = df.user_id[df.name==emp].iloc[0]
        users.append(user)
        cache.set(f'hrms_employee_children_{user}', json.dumps(users))
    cache.set('hrms_employee_children', df_.to_json())


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
    try:
        users = json.loads(frappe.cache.get(f'hrms_employee_children_{parent}'))
    except:
        users = []
    return users

    