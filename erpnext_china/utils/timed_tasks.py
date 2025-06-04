import math
import json
import hashlib
from datetime import datetime
import calendar

import frappe

from .wechat import api

def add_or_update_emp_checkin_log(hash_code, check_in_data, code, employee, update=False, doc_name=None):
	"""
	写入考勤记录
	"""
	checkin_time = datetime.fromtimestamp(check_in_data.get('checkin_time'))
	exception_type = check_in_data.get('exception_type')
	doc_data = {
		"employee": employee,
		"checkin_time": checkin_time,
		"user_id": check_in_data.get('userid', ''),
		"code": code,
		"group_id": check_in_data.get('groupid', ''),
		"schedule_id": check_in_data.get('schedule_id', ''),
		"timeline_id": check_in_data.get('timeline_id', ''),
		"group_name": check_in_data.get('groupname', ''),
		"exception_type": exception_type,
		"checkin_type": check_in_data.get('checkin_type', ''),
		"raw": check_in_data,
		"hash_code": hash_code
	}
	sch_checkin_time = check_in_data.get('sch_checkin_time')
	if sch_checkin_time:
		doc_data.update({"schedule_checkin_time": datetime.fromtimestamp(sch_checkin_time)})

	checkin_type = check_in_data.get('checkin_type')
	address = ','.join([check_in_data.get('location_title', ''), check_in_data.get('location_detail', '')])
	if checkin_type in ['上班打卡', '下班打卡']:
		doc_data.update({
			"location_or_device_id": address,
			"log_type": '内勤-考勤机',
		})
	else:
		doc_data.update({
			"address": address,
			"longitude": check_in_data.get('lng'),
			"latitude": check_in_data.get('lat'),
			"log_type": '外勤-手机定位',
		})
	if update:
		doc = frappe.get_doc("Employee Checkin Log", doc_name)
		doc.update(doc_data)
		doc.save(ignore_permissions=True)
	else:
		doc_data.update({"doctype": "Employee Checkin Log"})
		doc = frappe.get_doc(doc_data).insert(ignore_permissions=True)
	frappe.db.commit()


def get_today_timestamp():
	"""
	返回每天00:00:00 到当前的两个时间点
	"""
	now = datetime.now()
	year = now.year
	month = now.month
	day = now.day
	start_time = int(datetime(year, month, day, 0, 0, 0).timestamp())
	end_time = int(now.timestamp())
	return start_time, end_time


def get_temp_users():
	"""
	没有梳理好Employee和User中的数据时，暂时用
	"""
	users_id = [
		"liuyangguang@zhushigroup.cn",
	]
	users = []
	for uid in users_id:
		user = {"user": uid, "employee": "", "wecom": uid}
		custom_wecom_uid = frappe.db.get_value("User", uid, fieldname='custom_wecom_uid')
		if custom_wecom_uid:
			user.update({"wecom": custom_wecom_uid})
		employee_name = frappe.db.get_value("Employee", {"user_id": uid}, fieldname="name")
		if employee_name:
			user.update({"employee": employee_name})
		users.append(user)
	return users


def get_all_active_users():
	employees = frappe.get_all("Employee", filters={"status": 'Active'}, fields=["name", "user_id"])
	users = []
	for employee in employees:
		user = {"user": employee.user_id, "employee": employee.name, "wecom": employee.user_id}
		if employee.user_id:
			custom_wecom_uid = frappe.db.get_value("User", employee.user_id, fieldname='custom_wecom_uid')
			if custom_wecom_uid:
				user.update({"wecom": custom_wecom_uid})
			users.append(user)
	return users


def get_user_slices(users):
	# user 每次最多100
	slices = math.ceil(len(users) / 100)
	return [users[i*100:(i+1)*100] for i in range(slices)]


def trans_user_dict(users):
	result = {}
	for user in users:
		result.update({user.get('wecom'): user})
	return result


def has_exists(code):
	return frappe.db.exists("Employee Checkin Log", {"code": code})


def timestamp_to_str(dt:int, fmt: str=r"%Y-%m-%d %H:%M:%S"):
	return datetime.fromtimestamp(dt).strftime(fmt)


def get_exists_values(unique_code_list):
	return frappe.get_all(
		"Employee Checkin Log", 
		filters={"code": ['in', unique_code_list]}, 
		fields=["name", "hash_code", "code"])

def get_checkin_data(start_time=None, end_time=None):
	# [{user, employee, wecom}]
	all_users = get_all_active_users()
	# all_users = get_temp_users()
	setting = frappe.get_doc("WeCom Setting")
	access_token = setting.access_token
	if not access_token:
		return
	
	if not start_time or not end_time:
		start_time, end_time = get_today_timestamp()
		start_time = start_time - 24*60*60 # 为了获取企微校正后的打卡记录，每次同步时，同时同步前一天的打卡记录
		
	start_time = int(start_time)
	end_time = int(end_time)
	# [[0-100],[100-200],[200-267]]
	user_slices = get_user_slices(all_users)
	for users in user_slices:
		results = api.get_check_in_data(access_token, [user.get("wecom") for user in users], start_time, end_time)
		
		unique_code_hash_code_dict = {}
		unique_code_raw_dict = {}
		unique_code_list = []
		for result in results:
			hash_code = hashlib.md5(json.dumps(result).encode()).hexdigest()
			unique_code = '.'.join([str(result.get('userid')), str(result.get('checkin_time'))])

			unique_code_hash_code_dict[unique_code] = hash_code
			unique_code_raw_dict[unique_code] = result
			unique_code_list.append(unique_code)

		local_exists = get_exists_values(unique_code_list)
		local_codes = [local.code for local in local_exists]

		trans_users = trans_user_dict(users)
		
		# 新增的数据
		add_data = set(unique_code_list) - set(local_codes)
		for ucode in add_data:
			raw = unique_code_raw_dict[ucode]
			userid = raw.get('userid')
			employee = trans_users.get(userid).get('employee')
			add_or_update_emp_checkin_log(unique_code_hash_code_dict[ucode], raw, ucode, employee)
		
		# 更新数据
		for e in local_exists:
			local_hash_code = e.hash_code
			local_uique_code = e.code
			current_hash_code = unique_code_hash_code_dict.get(local_uique_code)
			if current_hash_code and local_hash_code != current_hash_code:
				raw =  unique_code_raw_dict.get(local_uique_code)
				userid = raw.get('userid')
				employee = trans_users.get(userid).get('employee')
				add_or_update_emp_checkin_log(current_hash_code, raw, local_uique_code, employee, update=True, doc_name=e.name)


@frappe.whitelist(allow_guest=True)
def task_get_check_in_data(start_time=None, end_time=None):
	frappe.enqueue(method=get_checkin_data, queue="long", timeout=3600, job_name="get_checkin_data", 
		start_time=start_time, end_time=end_time)


def disable_user(name):
	# 使用管理员账号进行修改
	doc = frappe.get_doc("User", name)
	try:
		if doc.enabled:
			doc.enabled = False
			doc.save(ignore_permissions=True)
	except:  # 有的可能因为信息不全在保存时报错
		pass


def get_checkin_day_data(first_day=None, last_day=None):
	all_users = get_all_active_users()
	# all_users = get_temp_users()
	setting = frappe.get_doc("WeCom Setting")
	access_token = setting.access_token
	
	if not access_token:
		return
	
	# 可以指定日期
	if not first_day or not last_day:
		first_day, last_day = get_current_month_first_last_day()
		first_day = first_day - 24*60*60 # 为了解决定时任务跨天的问题，往前推一天
	
	# [[0-100],[100-200],[200-267]]
	user_slices = get_user_slices(all_users)

	groups = frappe.get_all("Employee Checkin Group", fields=["group_name", "group_id"])
	existing_groups = {(group.group_name, str(group.group_id)) for group in groups}
	for users in user_slices:
		users_id = [user.get("wecom") for user in users]
		# 同步日报
		results = api.get_checkin_daydata_records(access_token, first_day, last_day, users_id)
		wecom_uids = [result['base_info']['acctid'] for result in results]
		user_ids = frappe.get_all("User", filters={"custom_wecom_uid": ['in', wecom_uids]}, fields=["name", "custom_wecom_uid"])
		wecom_uid_user_id = {u.custom_wecom_uid: u.name for u in user_ids}
		employee_ids = frappe.get_all("Employee", filters={"user_id": ["in", [u.name for u in user_ids]]}, fields=["name", "user_id", "department"])
		user_id_employee_id = {e.user_id: {'name': e.name, 'department': e.department} for e in employee_ids}

		doctype = "Employee Checkin Day Data"
		checkin_groups = {r['base_info']['rule_info']['groupname']:r['base_info']['rule_info']['groupid'] for r in results}
		add_checkin_group(existing_groups, checkin_groups)
		for result in results:
			new_unique_id = hashlib.md5(json.dumps(result).encode()).hexdigest()
			base_info = result['base_info']
			rule_info = base_info['rule_info']
			
			if frappe.db.get_value(doctype, {"unique_id": new_unique_id}):
				continue
			
			add_employee_checkin_day_data(result, base_info, rule_info, user_id_employee_id, wecom_uid_user_id, new_unique_id)


@frappe.whitelist(allow_guest=True)
def task_get_checkin_day_data(first_day=None, last_day=None):
	frappe.enqueue(method=get_checkin_day_data, queue="long", timeout=3600, job_name="get_checkin_day_data", 
		first_day=first_day, last_day=last_day)


def get_current_month_first_last_day():
	
	today = datetime.today()

	first_day_of_month = datetime(today.year, today.month, 1)

	_, last_day_of_month = calendar.monthrange(today.year, today.month)
	last_day_of_month = datetime(today.year, today.month, last_day_of_month)

	return int(first_day_of_month.timestamp()), int(last_day_of_month.timestamp())

def get_record_type(type_id):
	if not type_id:
		return '未知'
	record_types = {
		'1': '固定上下班',
		'2': '外出',
		'3': '按班次上下班',
		'4': '自由签到',
		'5': '加班',
		'7': '无规则'
	}
	return record_types.get(str(type_id))


def add_employee_checkin_day_data(result, base_info, rule_info, user_id_employee_id, wecom_uid_user_id, new_unique_id):
	doctype = "Employee Checkin Day Data"
	wecom_uid = base_info['acctid']
	info_date = timestamp_to_str(base_info['date'])
	day_data = frappe.db.get_value(doctype, filters={"date": info_date, 'acctid': wecom_uid}, fieldname=["name", "unique_id"], as_dict=True)

	info = {
		'date': info_date,
		'employee_name': base_info['name'],
		'employee': user_id_employee_id[wecom_uid_user_id[wecom_uid]]['name'],
		'department': user_id_employee_id[wecom_uid_user_id[wecom_uid]]['department'],
		'user': wecom_uid_user_id[wecom_uid],
		'acctid': wecom_uid,
		'record_type': get_record_type(base_info['record_type']),
		'group_name': rule_info['groupname'],
		'group_id': rule_info['groupid'],
		'schedule_name': rule_info['schedulename'],
		'schedule_id': rule_info['scheduleid'],
		'unique_id': new_unique_id,
		'raw': result
	}

	if day_data and new_unique_id != day_data.unique_id:
		# 更新
		doc = frappe.get_doc(doctype, day_data.name)
		for k, v in info.items():
			setattr(doc, k, v)
		doc.save(ignore_permissions=True)
	else:
		# 插入
		doc = frappe.new_doc(doctype)
		for k, v in info.items():
			setattr(doc, k, v)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()


def add_checkin_group(existing_groups, checkin_groups):

	for group_name, group_id in checkin_groups.items():
		group_id_str = str(group_id)
		if (group_name, group_id_str) not in existing_groups:
			doc = frappe.new_doc("Employee Checkin Group")
			doc.group_name = group_name
			doc.group_id = group_id_str
			doc.insert(ignore_permissions=True)
			

@frappe.whitelist(allow_guest=True)
def task_check_user_in_wecom():
	# 这里需要通过通讯录secret获取到单独的access_token
	access_token = api.get_access_token_by_secret()
	
	# 预定义白名单
	whitelist = [
		"Administrator",
		"api@api.com",
		"api001@api.com",
		"Guest",
		"admin2@zhushigroup.cn"
	]
	users = api.get_all_user_list_id(access_token)
	# 企微中所有的用户的id
	wecom_user_id_set = set([user.get("userid") for user in users])
	
	# 获取数据库中所有的user
	local_user_list = frappe.get_all("User", fields=["name", "custom_wecom_uid"])
	local_user_dict = {user.custom_wecom_uid: user.name for user in local_user_list}
	local_user_id_list = set(local_user_dict.keys())
	
	# 如果本地存在，企微不存在，则将用户关闭
	wecom_not_exist_users = local_user_id_list - wecom_user_id_set
	frappe.set_user('Administrator')
	for user in wecom_not_exist_users:
		if user:
			name = local_user_dict.get(user)
			if name not in whitelist:
				disable_user(name)
	frappe.db.commit()

			
