import math
import json
import hashlib
from datetime import datetime
import calendar

import frappe

from .wechat import api

def add_employee_checkin_log(check_in_data, code, employee):
	"""
	写入考勤记录
	"""
	checkin_time = datetime.fromtimestamp(check_in_data.get('checkin_time'))
	exception_type = check_in_data.get('exception_type')
	doc_data = {
		"doctype": "Employee Checkin Log",
		"employee": employee,
		"checkin_time": checkin_time,
		"code": code,
		"group_id": check_in_data.get('groupid', ''),
		"schedule_id": check_in_data.get('schedule_id', ''),
		"timeline_id": check_in_data.get('timeline_id', ''),
		"group_name": check_in_data.get('groupname', ''),
		"exception_type": exception_type,
		"raw": check_in_data
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
		"lilingyu@zhushigroup.cn",
		"yinzhenjiang@zhushigroup.cn",
		"wangmiao@zhushigroup.cn",
		"lixiulu@zhushigroup.cn",
		"houjun@zhushigroup.cn",
		"liuyangguang@zhushigroup.cn",
		"liziyuan@zhushigroup.cn",
		"yangzhen@zhushigroup.cn",
		"liuchao@zhushigroup.cn"
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


def get_exists_count(users, start_time, end_time):
	count = frappe.db.count("Employee Checkin Log", filters=[
		["checkin_time", "between", [
			timestamp_to_str(start_time), 
			timestamp_to_str(end_time)
		]],
		["employee", 'in', [user.get('employee') for user in users]]
	])
	return count or 0


@frappe.whitelist(allow_guest=True)
def task_get_check_in_data(start_time=None, end_time=None):
	# [{user, employee, wecom}]
	# all_users = get_all_active_users()
	all_users = get_temp_users()
	setting = frappe.get_doc("WeCom Setting")
	access_token = setting.access_token
	access_token = "hTJZxvHRiMTpIA6nfvRUjsjiKFucC09SmglDT57APkGCoSRcZJjQ3Z0EFuuzfFk6wBf5t1afS7wq0ujioMvkGme2lNV68V8wuSA1FtjTnz5rmBZQ3oe0RS-Mo6KcZi50inQ9JZ2yTM0X48GQBjo_QJIT366Jy-1t8ca5zeg-Zr3i2oqnWNIt0p1VzsXX29Lh3RPKHQk2zk3ycZs7Vasdbw"
	if not access_token:
		return
	
	if not start_time or not end_time:
		start_time, end_time = get_today_timestamp()
	
	# [[0-100],[100-200],[200-267]]
	user_slices = get_user_slices(all_users)
	for users in user_slices:
		results = api.get_check_in_data(access_token, [user.get("wecom") for user in users], start_time, end_time)
		local_exists_count = get_exists_count(users, start_time, end_time)
		
		# 当日已存在的记录个数和新拉取的数据个数一致说明无变化
		# 避免没有新数据增量出现也会执行has_exists去重操作
		# 过了四个打卡高峰期后，一般不会有新增量出现
		if local_exists_count >= len(results):
			continue
		
		trans_users = trans_user_dict(users)
		for result in results:
			# 这里的userid其实是我们User的custom_wecom_uid
			userid = result.get('userid')
			code = '.'.join([userid, str(result.get('checkin_time'))])

			# 每条数据根据 code 判重，code为索引字段
			if has_exists(code):
				continue

			employee = trans_users.get(userid).get('employee')
			add_employee_checkin_log(result, code, employee)


def disable_user(name):
	# 使用管理员账号进行修改
	doc = frappe.get_doc("User", name)
	try:
		if doc.enabled:
			doc.enabled = False
			doc.save(ignore_permissions=True)
	except:  # 有的可能因为信息不全在保存时报错
		pass

@frappe.whitelist(allow_guest=True)
def task_get_checkin_day_data(first_day=None, last_day=None):
	# all_users = get_all_active_users()
	all_users = get_temp_users()
	setting = frappe.get_doc("WeCom Setting")
	access_token = setting.access_token
	access_token = "hTJZxvHRiMTpIA6nfvRUjsjiKFucC09SmglDT57APkGCoSRcZJjQ3Z0EFuuzfFk6wBf5t1afS7wq0ujioMvkGme2lNV68V8wuSA1FtjTnz5rmBZQ3oe0RS-Mo6KcZi50inQ9JZ2yTM0X48GQBjo_QJIT366Jy-1t8ca5zeg-Zr3i2oqnWNIt0p1VzsXX29Lh3RPKHQk2zk3ycZs7Vasdbw"
	
	if not access_token:
		return
	
	# 可以指定日期
	if not first_day or not last_day:
		first_day, last_day = get_current_month_first_last_day()
	
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

			
