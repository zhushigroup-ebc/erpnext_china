import frappe
import json
import requests
import xmltodict
import base64
from datetime import datetime
from werkzeug.wrappers import Response

from frappe.utils import logger, get_url

from . import WXBizMsgCrypt3
from erpnext_china.utils import lead_tools


logger.set_log_level("DEBUG")
logger = frappe.logger("wx-message", allow_site=True, file_count=10)

def get_url_params(kwargs: dict):
	raw_signature = kwargs.get('msg_signature')
	raw_timestamp = kwargs.get('timestamp')
	raw_nonce = kwargs.get('nonce')
	raw_echostr = kwargs.get('echostr', None)
	return raw_signature, raw_timestamp, raw_nonce, raw_echostr


def get_wx_nickname(external_user_id):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get'
	wecom_setting = frappe.get_doc("WeCom Setting")
	params = {
		'access_token': wecom_setting.access_token,
		'external_userid': external_user_id
	}
	try:
		resp = requests.get(url, params=params)
		result = resp.json()
		external_contact = result.get('external_contact')
		return external_contact.get('name')
	except Exception as e:
		logger.warning(e)
		return None


def get_tag_staff(tag_id, access_token):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/tag/get'
	params = {
		'access_token': access_token,
		'tagid': tag_id
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	return result.get('userlist')


def get_checkin_group(access_token: str):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/checkin/getcorpcheckinoption'

	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	return result.get('group')


def get_tags(access_token: str):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/tag/list'
	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	# tagid  tagname
	return result.get('taglist')



def get_check_in_data(access_token: str, users: list[str], starttime: int, endtime: int, opencheckindatatype:int=3):
	"""
	请求考勤记录
	"""
	url = "https://qyapi.weixin.qq.com/cgi-bin/checkin/getcheckindata?access_token=" + access_token
	# opencheckindatatype 打卡类型。1：上下班打卡；2：外出打卡；3：全部打卡
	data = {
		"opencheckindatatype": opencheckindatatype,
		"starttime": starttime,
		"endtime": endtime,
		"useridlist": users
	}
	res = requests.post(url, json=data)
	result = res.json()
	return result.get('checkindata', [])


def get_checkin_daydata_records(access_token, starttime, endtime, useridlist):
	"""获取打卡日报数据"""
	checkin_url = f"https://qyapi.weixin.qq.com/cgi-bin/checkin/getcheckin_daydata?access_token={access_token}"
	params = {
		"starttime": starttime,
		"endtime": endtime,
		"useridlist": useridlist
	}
	checkin_response = requests.post(checkin_url, json=params)
	checkin_response.raise_for_status() 
	result = checkin_response.json()
	return result.get('datas', [])


def get_departments(access_token: str):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/department/list'
	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	return result.get('department')


def get_staff_from_department(department: dict, access_token: str):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist'
	params = {
		'access_token': access_token,
		'department_id': department.get('id')
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	# return result.get('userlist')
	return [
		{
			"user_id": user.get('userid'), 
			"user_name": user.get('name'), 
			"department_id": department.get('id'),
			"department_name": department.get('name')
		} for user in result.get('userlist')
	]

def check_wecom_user(user_id, access_token):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/user/get'

	params = {
		'access_token': access_token,
		'userid': user_id,
	}
	try:
		resp = requests.get(url, params=params)
		result = resp.json()
		# {'errcode': 60111, 'errmsg': 'invalid string value `FuLiJun1`. userid not found', ...}
		# 60111 表示企微没有此用户
		if result.get("errcode") == 60111:
			return False
		return True
	except Exception as e:
		# 如果因为网络问题等因素导致错误，则返回True
		return True


def delete_checkin_group(access_token, group_id):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/checkin/del_checkin_option'
	params = {
		'access_token': access_token
	}
	data = {
		"groupid": group_id,
		"effective_now": True
	}
	resp = requests.post(url, params=params, json=data)
	result = resp.json()
	logger.info(result)

	if result.get('errcode') != 0:
		frappe.throw("考勤规则删除失败！" + result.get('errmsg', ''))


def clean_checkin_group_params(group: dict):
	# wifimac_infos 和 loc_infos必须设置一个
	if not group.get('wifimac_infos', []) and not group.get('loc_infos', []):
		group['loc_infos'] = [
			{
				"lat": 36663583,  # 纬度
				"lng": 117008871,  # 经度
				"loc_title": "绿地中心",
				"loc_detail": "山东省济南市市中区共青团路25号",
				"distance": 100
			}
		]
	# 先清空range
	group['range']['userid'] = []
	group['range']['party_id'] = []
	group['range']['tagid'] = []
	group.pop("create_time", None)
	group.pop("create_userid", None)
	group.pop('update_userid', None)
	group.pop('updatetime', None)
	# ot_info已经被ot_info_v2代替了，参数中有ot_info会报错
	group.pop('ot_info', None)

	# 当checkindate.allow_flex 为false时
	for checkindate in group.get('checkindate', []):
		if not checkindate.get('allow_flex', False):
			checkindate.pop("late_rule", None)
			checkindate.pop('flex_on_duty_time', None)
			checkindate.pop('flex_off_duty_time', None)
			checkindate.pop('max_allow_arrive_early', None)
			checkindate.pop('max_allow_arrive_late', None)

		for checkintime in checkindate.get('checkintime', []):
			if not checkintime.get('allow_rest', False):
				checkintime.pop('rest_begin_time', None)
				checkintime.pop('rest_end_time', None)
	
	# schedulelist
	for schedulelist in group.get('schedulelist', []):
		if not schedulelist.get('allow_flex', False):
			schedulelist.pop('flex_on_duty_time', None)
			schedulelist.pop('flex_off_duty_time', None)
			schedulelist.pop('late_rule', None)
			schedulelist.pop('limit_aheadtime', None)
			schedulelist.pop('limit_offtime', None)
			schedulelist.pop('noneed_offwork', None)
			schedulelist.pop('flex_time', None)
		for time_section in schedulelist.get('time_section', []):
			if not time_section.get('allow_rest', False):
				time_section.pop('rest_begin_time', None)
				time_section.pop('rest_end_time', None)
	
	buka_remind = group.get('buka_remind', {})
	if not buka_remind.get('open_remind', False):
		buka_remind.pop('buka_remind_day', None)
		buka_remind.pop('buka_remind_month', None)
	return group

def create_checkin_group(access_token, group, effective_now=False):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/checkin/add_checkin_option'
	params = {
		'access_token': access_token
	}
	data = {
		'effective_now': effective_now,
		'group': group
	}
	resp = requests.post(url, params=params, json=data)
	result = resp.json()
	logger.info(result)

	if result.get('errcode') != 0:
		frappe.throw("考勤规则创建失败！" + result.get('errmsg', ''))
	

def update_checkin_group(access_token, group: dict, effective_now=False):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/checkin/update_checkin_option'
	params = {
		'access_token': access_token
	}
	data = {
		'effective_now': effective_now,
		'group': group
	}
	resp = requests.post(url, params=params, json=data)
	result = resp.json()
	logger.info(result)

	if result.get('errcode') != 0:
		frappe.throw("考勤规则修改失败！" + result.get('errmsg', ''))

def get_access_token_by_secret():
	url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
	params = {
		'corpid': 'wwb5d592cbfd08e9b1',
		'corpsecret': 'pYH-hX3jAPSSqHMEiOCX2hwhNlmXQqN9yLpo39qBBKE'
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	access_token = result.get('access_token')
	return access_token

def get_all_user_list_id(access_token):
	# 必须通过通讯录同步Secret获取
	url = 'https://qyapi.weixin.qq.com/cgi-bin/user/list_id'
	params = {
		'access_token': access_token
	}
	resp = requests.post(url, params=params)
	result = resp.json()
	return result.get('dept_user')

def get_raw_request(url, raw_xml_data):
	if isinstance(raw_xml_data, str):
		body = raw_xml_data
	elif isinstance(raw_xml_data, bytes):
		body = base64.b64encode(raw_xml_data).decode()
	else:
		body = ''
	raw_request = {
		"url": url,
		"body": body
	}
	return raw_request


def qv_create_crm_lead(message=None, original_lead=None):
	try:
		if message:
			state = str(message.state)[2:-1]
			if state:
				original_lead_doc = lead_tools.search_original_lead(state)
				if original_lead_doc:
					euid = str(message.external_user_id)
					wx_nickname = get_wx_nickname(euid)
					lead_tools.create_crm_lead_by_message(message, original_lead_doc, wx_nickname)
		
		if original_lead:
			bd_vid = original_lead.bd_vid
			if bd_vid:
				message_doc = lead_tools.search_wecom_message(bd_vid)
				if message_doc:
					euid = str(message_doc.external_user_id)
					wx_nickname = get_wx_nickname(euid)
					lead_tools.create_crm_lead_by_message(message_doc, original_lead, wx_nickname)
	except Exception as e:
		logger.error(e)


def update_card_template(response_code, from_user, confirm_code):
	wecom_setting = frappe.get_doc("WeCom Setting")
	access_token = wecom_setting.access_token
	url = "https://qyapi.weixin.qq.com/cgi-bin/message/update_template_card"
	params = {
		'access_token': access_token
	}
	msg = '已确认信息正确'
	if confirm_code != '1':
		msg = '已确认信息有误，请联系柴春燕同事进行修改'
	data = {
		"userids" : [from_user],
		"agentid" : 1000008,
		"response_code": response_code,
		"button":{
			"replace_name": msg
		}
	}
	resp = requests.post(url, params=params, json=data)


@frappe.whitelist(allow_guest=True)
def wechat_msg_callback(**kwargs):
	url = get_url() + frappe.request.full_path
	# 验证URL合法性
	api_setting = frappe.get_cached_doc("WeCom MsgApi Setting")
	wecom_setting = frappe.get_cached_doc("WeCom Setting")
	client = WXBizMsgCrypt3.WXBizMsgCrypt(api_setting.token, api_setting.key, wecom_setting.client_id)
	raw_signature, raw_timestamp, raw_nonce, raw_echostr = get_url_params(kwargs)
	# 如果存在 echostr 说明是首次配置发送的验证性请求
	if raw_echostr:
		code, text = client.VerifyURL(raw_signature, raw_timestamp, raw_nonce, raw_echostr)
		return Response(text)
	
	# 其它的回调事件
	raw_xml_data = frappe.local.request.data
	try:
		code, xml_content = client.DecryptMsg(raw_xml_data, raw_signature, raw_timestamp, raw_nonce)
		if not xml_content:
			logger.warning("xml_content is None")
			return
		
		dict_content = xmltodict.parse(xml_content)
		dict_data = dict_content.get('xml')
		change_type = dict_data.get('ChangeType')

		response_code = dict_data.get('ResponseCode')
		if response_code:
			event_key = dict_data.get('EventKey')
			str_list = str(event_key).split('_')
			employee_name = str_list[0]
			confirm_code = str_list[1]
			from_user = dict_data.get('FromUserName')
			update_card_template(response_code, from_user, confirm_code)
			if frappe.db.exists('WeCom Message Confirmation', employee_name):
				doc = frappe.get_doc('WeCom Message Confirmation', employee_name)
			else:
				doc = frappe.new_doc('WeCom Message Confirmation')
				doc.employee = employee_name
			if confirm_code == '1':
				doc.right = 1
				doc.error = 0
			else:
				doc.error = 1
				doc.right = 0
			doc.save(ignore_permissions=True)

		# 如果是获客助手新增客户
		if change_type == 'add_external_contact':
			external_user_id = dict_data.get('ExternalUserID')
			state = dict_data.get('State')
			msg = frappe.db.exists('WeCom Message', {"external_user_id": external_user_id})
			if  state and msg is None:
				raw_request = get_raw_request(url, raw_xml_data)
				message = lead_tools.save_message(dict_data, json.dumps(raw_request))
				if message:
					qv_create_crm_lead(message)
				dict_data.update({"record_id": message.name if message else ''})
			logger.info(dict_data)
			frappe.db.commit()

			return
	except Exception as e:
		logger.error(e)


@frappe.whitelist()
def msg_create_lead_handler(**kwargs):
	original_lead_name = kwargs.get('original_lead')
	message_name = kwargs.get('message')
	if not original_lead_name or not message_name:
		raise frappe.ValidationError("original lead and message are required!")
	try:
		original_lead_doc = frappe.get_doc("Original Leads", original_lead_name)
		message_doc = frappe.get_doc("WeCom Message", message_name)
		euid = str(message_doc.external_user_id)
		wx_nickname = get_wx_nickname(euid)
		lead_tools.create_crm_lead_by_message(message_doc, original_lead_doc, wx_nickname)
	except Exception as e:
		logger.error(e)
		raise frappe.ValidationError("crm lead creation failed!")