# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkaddress_purification.request.v20191118.ExtractNameRequest import ExtractNameRequest
from aliyunsdkaddress_purification.request.v20191118.ExtractPhoneRequest import ExtractPhoneRequest
from aliyunsdkaddress_purification.request.v20191118.StructureAddressRequest import StructureAddressRequest
from aliyunsdkaddress_purification.request.v20191118.ExtractAddressRequest import ExtractAddressRequest


class AliyunSettings(Document):
	pass

settings = frappe.get_single('Aliyun Settings')
def get_client():
	return AcsClient(
		settings.api_key,
		settings.api_secret,
		"cn-hangzhou"
	)

@frappe.whitelist()
def structure_address(text):
    client = get_client()
    if not client:
        return {}
    # 构建request
    request = StructureAddressRequest()
    request.set_ServiceCode("addrp")
    request.set_AppKey(settings.app_key)
    request.set_Text(text)
    response = client.do_action_with_exception(request)
    # 处理请求结果
    return json.loads(response)['Data']

@frappe.whitelist()
def extract_name(text):
    client = get_client()
    if not client:
        return {}
    request = ExtractNameRequest()
    request.set_ServiceCode("addrp")
    request.set_AppKey(settings.app_key)
    request.set_Text(text)
    response = client.do_action_with_exception(request)
    return json.loads(response)['Data']

@frappe.whitelist()
def extract_phone(text):
    client = get_client()
    if not client:
        return {}
    request = ExtractPhoneRequest()
    request.set_ServiceCode("addrp")
    request.set_AppKey(settings.app_key)
    request.set_Text(text)
    response = client.do_action_with_exception(request)
    return json.loads(response)['Data']

@frappe.whitelist()
def extract_address(text):
    client = get_client()
    if not client:
        return {}
    request = ExtractAddressRequest()
    request.set_ServiceCode("addrp")
    request.set_AppKey(settings.app_key)
    request.set_Text(text)
    response = client.do_action_with_exception(request)
    return json.loads(response)['Data']

@frappe.whitelist()
def get_address_details(text):
    res = {}
    try:
        structure_addr = json.loads(structure_address(text))['structure']
        res.update(parse_custom_string(structure_addr))
    except Exception as e:
        frappe.log_error(title="Error in get structure address", message=frappe.get_traceback())

    try:
        person_extract = json.loads(extract_name(text))['person_extract'][0].get('word')
        res.update({'contact':person_extract})
    except Exception as e:
        pass
    
    try:
        phone_extract = json.loads(extract_phone(text))['phone_extract'][0].get('word')
        res.update({'phone':phone_extract})
    except Exception as e:
        pass

    try:
        address = json.loads(extract_address(text))['location_extract'][0].get('word')
        res.update({'address':address})
    except Exception as e:
        pass

    return res

def parse_custom_string(s):
    result = {}
    pairs = s.split('\t')
    for pair in pairs:
        if '=' not in pair:
            continue
        key, value = pair.split('=', 1)
        if key in ['prov','city','district','devzone']:
            result[key] = value
    return result