# Copyright (c) 2026, Digitwise Ltd. and contributors
# For license information, please see license.txt

import copy
import json
import secrets
import requests
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from erpnext_china.utils import lead_tools
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import logger
from typing import Optional, List, Dict, Any

logger.set_log_level("DEBUG")
local_lead_logger = frappe.logger("local-lead", allow_site=True, file_count=10)

# ==================== API 配置 ====================
API_BASE_URL = "https://api.oceanengine.com"
AD_BASE_URL = "https://ad.oceanengine.com"

# 线索相关
API_PATH_CLUE_LIST = "/open_api/2/tools/clue/life/get/"
API_PATH_CLUE_CALLBACK = "/open_api/2/tools/clue/life/callback/"
API_PATH_CLUE_FOLLOW_UPDATE = "/open_api/2/tools/clue/life/follow/update/"
API_PATH_BATCH_CALLBACK = "/open_api/2/tools/clue/batch_callback/"

# OAuth 相关
OAUTH_AUTHORIZE_URL = "https://open.oceanengine.com/audit/oauth.html"
OAUTH_TOKEN_URL = "https://ad.oceanengine.com/open_api/oauth2/access_token/"
OAUTH_REFRESH_URL = "https://ad.oceanengine.com/open_api/oauth2/refresh_token/"
OAUTH_ADVERTISER_GET_URL = "https://api.oceanengine.com/open_api/oauth2/advertiser/get/"

# 工作台账户列表
CUSTOMER_CENTER_ADVERTISER_LIST_URL = "https://ad.oceanengine.com/open_api/2/customer_center/advertiser/list/"

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒


class LeadDomainforLocal(Document):
    pass


def split_location(location: str):
    """解析位置信息，返回 (省份, 城市)
    处理格式：省份+城市 或 单一位置
    """
    if not location:
        return "", ""
    if "+" not in location:
        return location, location
    province_city = location.split('+')
    return tuple(province_city)


def build_url(path, query=""):
    """构建请求URL"""
    return f"{API_BASE_URL}{path}"


def get_flow_type_str(flow_type: str):
    """获取流量类型描述"""
    flow_types = {
        "AD": "广告流量",
        "NATURE": "自然流量",
        "SEARCH": "搜索流量",
    }
    return flow_types.get(flow_type, flow_type or '未知')


def get_clue_type_str(clue_type: str):
    """获取线索类型描述"""
    clue_types = {
        "GROUP_BUYING": "团购",
        "FORM": "表单",
        "CONSULT": "咨询",
        "PHONE": "电话",
        "COUPON": "卡券",
        "RESERVATION": "预约",
    }
    return clue_types.get(clue_type, clue_type or '未知')


def get_action_type_str(action_type: str):
    """获取行为类型描述"""
    action_types = {
        "LIVE_VIDEO": "直播",
        "SHORT_VIDEO": "短视频",
        "STORE": "门店",
        "SEARCH": "搜索",
    }
    return action_types.get(action_type, action_type or '未知')


def get_effective_state_str(effective_state: int):
    """获取有效状态描述"""
    effective_states = {
        200: "待确认",
        201: "确认有效",
        202: "确认无效",
        203: "已退款",
        204: "到店",
        205: "成交",
    }
    if effective_state is None:
        return ''
    return effective_states.get(effective_state, str(effective_state))


def get_follow_state_str(follow_state: str):
    """获取跟进状态描述"""
    follow_states = {
        "NOT_CALLED": "未跟进",
        "FOLLOWING": "跟进中",
        "FINISHED": "已成交",
        "INVALID": "无效",
    }
    return follow_states.get(follow_state, follow_state or '')


def get_leads_page_str(leads_page: str):
    """获取线索页面来源描述"""
    leads_pages = {
        "PRODUCT_DETAIL": "商品详情页",
        "STORE_HOME": "门店首页",
        "COUPON_CENTER": "卡券中心",
        "SEARCH": "搜索结果页",
        "OTHER": "其他",
    }
    return leads_pages.get(leads_page, leads_page or '')


def get_allocation_status_str(allocation_status: str):
    """获取分配状态描述"""
    allocation_statuses = {
        "NOT_ASSIGN": "未分配",
        "ASSIGNED": "已分配",
        "ALLOCATING": "分配中",
    }
    return allocation_statuses.get(allocation_status, allocation_status or '')


def get_effective_state_name_str(effective_state_name: str):
    """获取有效状态名称描述（字符串版本）"""
    effective_state_names = {
        "NOT_MARKED": "未标记",
        "EFFECTIVE": "有效",
        "INVALID": "无效",
        "REFUNDED": "已退款",
        "ARRIVED": "已到店",
        "DEAL": "已成交",
    }
    return effective_state_names.get(effective_state_name, effective_state_name or '')


def get_follow_life_account_type_str(account_type: str):
    """获取关注的生活号类型描述"""
    account_types = {
        "HEAD": "总店",
        "BRANCH": "分店",
        "FRANCHISE": "加盟店",
    }
    return account_types.get(account_type, account_type or '')


def get_qcpx_ticket_status_str(ticket_status: str):
    """获取券状态描述"""
    ticket_statuses = {
        "NOTICKET": "无券",
        "NOT_USED": "未使用",
        "USED": "已使用",
        "EXPIRED": "已过期",
        "REFUNDED": "已退款",
    }
    return ticket_statuses.get(ticket_status, ticket_status or '')


def get_order_status_str(order_status: str):
    """获取订单状态描述"""
    order_statuses = {
        "CREATED": "已创建",
        "PAID": "已支付",
        "COMPLETED": "已完成",
        "CANCELLED": "已取消",
        "REFUNDED": "已退款",
    }
    return order_statuses.get(order_status, order_status or '')


def api_request_with_retry(method: str, url: str, headers: dict, payload: dict = None, max_retries: int = MAX_RETRIES) -> Optional[dict]:
    """
    带重试机制的API请求
    
    :param method: 请求方法 (GET/POST)
    :param url: 请求URL
    :param headers: 请求头
    :param payload: 请求数据
    :param max_retries: 最大重试次数
    :return: API响应数据
    """
    for attempt in range(max_retries):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=payload, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            response.raise_for_status()
            result = response.json()
            
            # 检查API业务错误码
            if result.get('code') != 0:
                error_code = result.get('code')
                error_msg = result.get('message', '未知错误')
                
                # 可重试的错误码
                if error_code in [100125]:  # 网络异常
                    if attempt < max_retries - 1:
                        local_lead_logger.warning(f"API请求失败(错误码{error_code})，{RETRY_DELAY}秒后重试... (第{attempt + 1}次)")
                        time.sleep(RETRY_DELAY)
                        continue
                
                local_lead_logger.error(f"API业务错误: code={error_code}, message={error_msg}")
            
            return result
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                local_lead_logger.warning(f"API请求超时，{RETRY_DELAY}秒后重试... (第{attempt + 1}次)")
                time.sleep(RETRY_DELAY)
                continue
            local_lead_logger.error("API请求超时，已达最大重试次数")
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                local_lead_logger.warning(f"API请求失败: {e}，{RETRY_DELAY}秒后重试... (第{attempt + 1}次)")
                time.sleep(RETRY_DELAY)
                continue
            local_lead_logger.error(f"API请求失败: {e}")
    
    return None


def fetch_local_leads(access_token: str, local_account_ids: list, start_time: str, end_time: str, page: int = 1, page_size: int = 100):
    """
    调用巨量开放平台API获取本地推线索列表
    
    :param access_token: 访问令牌
    :param local_account_ids: 本地账户ID列表
    :param start_time: 开始时间 (格式: YYYY-MM-DD HH:MM:SS)
    :param end_time: 结束时间 (格式: YYYY-MM-DD HH:MM:SS)
    :param page: 页码
    :param page_size: 每页数量，最大100
    :return: API响应数据
    """
    url = build_url(API_PATH_CLUE_LIST)
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json",
    }
    
    payload = {
        "local_account_ids": local_account_ids,
        "start_time": start_time,
        "end_time": end_time,
        "page": page,
        "page_size": page_size
    }
    
    return api_request_with_retry('POST', url, headers, payload)


def clue_callback(access_token: str, advertiser_id: int, clue_id: str, event_type: str, 
                  convert_state: int = None, pay_amount: int = None, occur_time: str = None, remark: str = None) -> dict:
    """
    线索回传 - 将转化数据回传到巨量平台
    
    :param access_token: 访问令牌
    :param advertiser_id: 广告主ID
    :param clue_id: 线索ID
    :param event_type: 事件类型 (如: FORM_SUBMIT, SMART_CALL, CONSULT 等)
    :param convert_state: 转化状态 (1-有效, 2-无效, 3-待确认)
    :param pay_amount: 支付金额（分）
    :param occur_time: 发生时间
    :param remark: 备注
    :return: API响应
    """
    url = build_url(API_PATH_CLUE_CALLBACK)
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json",
    }
    
    payload = {
        "advertiser_id": advertiser_id,
        "clue_id": clue_id,
        "event_type": event_type,
    }
    
    if convert_state is not None:
        payload["convert_state"] = convert_state
    if pay_amount is not None:
        payload["pay_amount"] = pay_amount
    if occur_time:
        payload["occur_time"] = occur_time
    if remark:
        payload["remark"] = remark
    
    return api_request_with_retry('POST', url, headers, payload)


def batch_clue_callback(access_token: str, advertiser_id: int, clue_list: List[Dict[str, Any]]) -> dict:
    """
    批量线索回传
    
    :param access_token: 访问令牌
    :param advertiser_id: 广告主ID
    :param clue_list: 线索列表，每个元素包含 clue_id, event_type, convert_state 等
    :return: API响应
    """
    url = build_url(API_PATH_BATCH_CALLBACK)
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json",
    }
    
    payload = {
        "advertiser_id": advertiser_id,
        "clue_list": clue_list,
    }
    
    return api_request_with_retry('POST', url, headers, payload)


def update_clue_follow_status(access_token: str, advertiser_id: int, clue_id: str, 
                               follow_status: int, remark: str = None) -> dict:
    """
    更新线索跟进状态
    
    :param access_token: 访问令牌
    :param advertiser_id: 广告主ID
    :param clue_id: 线索ID
    :param follow_status: 跟进状态 (1-未跟进, 2-跟进中, 3-已成交, 4-无效)
    :param remark: 备注
    :return: API响应
    """
    url = build_url(API_PATH_CLUE_FOLLOW_UPDATE)
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json",
    }
    
    payload = {
        "advertiser_id": advertiser_id,
        "clue_id": clue_id,
        "follow_status": follow_status,
    }
    
    if remark:
        payload["remark"] = remark
    
    return api_request_with_retry('POST', url, headers, payload)


def process_local_lead(lead_data: dict, local_account: Document):
    """
    处理单条本地推线索数据，保存到ERPNext
    
    :param lead_data: 线索数据
    :param local_account: 本地推账户文档
    """
    clue_id = str(lead_data.get('clue_id', ''))
    local_lead_logger.error(f"增加一条记录以显示执行了同步功能")

    if not clue_id:
        return None

    # 检查线索是否已存在
    # 由于实现了原始线索和CRM线索的级联删除，只需要检查原始线索是否存在即可
    record = lead_tools.get_doc_or_none('Original Leads', {'clue_id': clue_id})
    
    user, employee = None, None
    if local_account and local_account.employee:
        employee = lead_tools.get_doc_or_none('Employee', {"name": local_account.employee})
    if employee:
        user = employee.user_id
    if user:
        frappe.set_user(user)
    
    if not record:
        # 提取线索基本信息
        lead_name = lead_data.get('name', '匿名') or '匿名'
        telephone = lead_data.get('telephone', '')
        weixin = lead_data.get('weixin', '')
        province_name = lead_data.get('province_name') or lead_data.get('auto_province_name', '')
        city_name = lead_data.get('city_name') or lead_data.get('auto_city_name', '')
        county_name = lead_data.get('county_name', '')
        
        # 转换类型描述
        flow_type_name = get_flow_type_str(lead_data.get('flow_type', ''))
        clue_type_name = get_clue_type_str(lead_data.get('clue_type', ''))
        action_type_name = get_action_type_str(lead_data.get('action_type', ''))

        # 转换状态描述
        follow_state_name = get_follow_state_str(lead_data.get('follow_state', ''))
        leads_page_name = get_leads_page_str(lead_data.get('leads_page', ''))
        allocation_status_name = get_allocation_status_str(lead_data.get('allocation_status', ''))
        effective_state_name = get_effective_state_name_str(lead_data.get('effective_state_name', ''))
        account_type_name = get_follow_life_account_type_str(lead_data.get('follow_life_account_type', ''))
        ticket_status_name = get_qcpx_ticket_status_str(lead_data.get('qcpx_ticket_status', ''))
        order_status_name = get_order_status_str(lead_data.get('order_status', ''))
        
        # 处理时间
        create_time_str = lead_data.get('create_time_detail', '')
        commit_time = None
        if create_time_str:
            try:
                commit_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        # 处理标签
        system_tags = lead_data.get('system_tags', [])
        tags = lead_data.get('tags', [])
        system_tags_str = json.dumps(system_tags, ensure_ascii=False) if system_tags else ''
        tags_str = json.dumps(tags, ensure_ascii=False) if tags else ''
        
        # 构建原始线索数据
        original_lead_data = {
            'doctype': 'Original Leads',
            'source': 'Local',  # 本地推的 source 值必须为 Local（对应字段选项）
            'original_json_data': copy.deepcopy(lead_data),
            'clue_id': clue_id,
            'lead_name': lead_name,
            'clue_phone_number': telephone,
            'wechat_account': weixin,
            'area': city_name,
            'area_province': province_name,
            'county_name': county_name,
            'address': lead_data.get('address', ''),
            'commit_time': commit_time,
            'gender': lead_data.get('gender', ''),
            'age': str(lead_data.get('age', '')) if lead_data.get('age') else '',
            'clue_source': '字节-本地推',
            'flow_type': flow_type_name,
            'clue_type': clue_type_name,
            'created_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'employee_local_account': local_account.name if local_account else None,
            'user': user,  # 从员工信息中获取user
            'product_category': local_account.product_category if local_account and local_account.product_category else None,
            # 本地推特有字段
            'promotion_id': str(lead_data.get('promotion_id', '')) if lead_data.get('promotion_id') else '',
            'promotion_name': lead_data.get('promotion_name', ''),
            'adv_name': lead_data.get('advertiser_name', ''),
            'remark': lead_data.get('remark', ''),
            'remark_dict': lead_data.get('remark_dict', ''),
            'req_id': lead_data.get('req_id', ''),
            'search_word': lead_data.get('search_bid_word', ''),
            # 本地推专有字段
            'action_type': action_type_name,
            'allocation_status': allocation_status_name,
            'effective_state': lead_data.get('effective_state', ''),
            'effective_state_name': effective_state_name,
            'follow_state_name': follow_state_name,
            'leads_page': leads_page_name,
            'order_status': order_status_name,
            'follow_life_account_id': lead_data.get('follow_life_account_id', ''),
            'follow_life_account_name': lead_data.get('follow_life_account_name', ''),
            'follow_life_account_type': account_type_name,
            'clue_owner_name': lead_data.get('clue_owner_name', ''),
            'content_id': lead_data.get('content_id', ''),
            'tool_id': lead_data.get('tool_id', ''),
            'order_id': str(lead_data.get('order_id', '')) if lead_data.get('order_id') else '',
            'qcpx_ticket_status': ticket_status_name,
            'qcpx_ticket_info': lead_data.get('qcpx_ticket_info', ''),
            'system_tags': system_tags_str,
            'tags': tags_str,
        }
        
        try:
            # 尝试创建原始线索
            original_lead_doc = frappe.get_doc(original_lead_data).insert(ignore_permissions=True)
            local_lead_logger.info(f"创建原始线索成功: {original_lead_doc.name}")

            # 标记为新创建的文档（用于后续判断是否为新增）
            original_lead_doc._is_newly_created = True

            # 同时生成一条CRM数据
            clue_source_name = lead_tools.get_or_insert_flow_channel_name('本地推', '字节')

            # 检查是否需要产品类别
            pc_value = local_account.product_category if local_account and local_account.product_category else None
            auto_alloc = local_account.auto_allocation if local_account else False

            # 如果启用了自动分配但没有产品类别，记录警告
            if auto_alloc and not pc_value:
                local_lead_logger.warning(f"账户 {local_account.local_account_id if local_account else 'unknown'} 启用了自动分配但未设置产品类别")

            try:
                # 先检查CRM线索是否已存在
                crm_lead_doc = None
                links = lead_tools.get_single_contact_info(telephone, '', weixin)
                if links:
                    # 查找是否存在匹配的线索
                    or_filters = [
                        {'phone': ['in', links]},
                        {'mobile_no': ['in', links]},
                        {'custom_wechat': ['in', links]}
                    ]
                    crm_leads = frappe.get_all("Lead", or_filters=or_filters, fields=['name', 'lead_owner'])
                    if crm_leads:
                        # 如果有多条匹配的线索，取第一条作为主要关联 zhouzx 暂时先按照这个处理
                        crm_lead_doc = lead_tools.get_doc_or_none('Lead', crm_leads[0].name)

                        # 给所有匹配的线索负责人发送站内消息
                        recipients = []
                        for lead_info in crm_leads:
                            if lead_info.get('lead_owner') and lead_info['lead_owner'] not in recipients:
                                recipients.append(lead_info['lead_owner'])

                        if recipients:
                            message = f"有新的原始线索【{original_lead_doc.name}】关联到您的CRM线索。"
                            # 发送站内通知
                            for recipient in recipients:
                                notification_doc = frappe.get_doc({
                                    'doctype': 'Notification Log',
                                    'subject': f"新原始线索关联: {original_lead_doc.name}",
                                    'for_user': recipient,
                                    'type': 'Alert',
                                    'document_type': 'Original Leads',
                                    'document_name': original_lead_doc.name,
                                    'message': message,
                                    'from_user': frappe.session.user
                                })
                                notification_doc.insert(ignore_permissions=True)
                            local_lead_logger.info(f"已发送站内消息给 {len(recipients)} 个负责人，关联原始线索: {original_lead_doc.name}")

                    if not crm_leads:
                        # CRM线索不存在，执行创建
                        crm_lead_doc = lead_tools.get_or_insert_crm_lead(
                            lead_name,
                            clue_source_name,
                            telephone,
                            '',
                            weixin,
                            city_name,
                            province_name,
                            original_lead_name=original_lead_doc.name,
                            commit_time=original_lead_doc.commit_time or original_lead_doc.created_datetime,
                            keyword='',
                            search_word=lead_data.get('search_bid_word', ''),
                            auto_allocation=auto_alloc,
                            local_account=local_account.name if local_account else None,
                            product_category=pc_value,
                        )
            except Exception as crm_e:
                # CRM 线索创建失败，但不影响原始线索的保存
                local_lead_logger.error(f"创建CRM线索失败 clue_id={clue_id}: {crm_e}")
                crm_lead_doc = None

            # 添加crm 线索和原始线索之间的关系
            if crm_lead_doc:
                original_lead_doc.crm_lead = crm_lead_doc.name
                # 如果 CRM 线索已存在（不是新创建的），使用 CRM 线索的 owner 作为原始线索的 user
                if not user and crm_lead_doc.owner:
                    original_lead_doc.user = crm_lead_doc.owner
                original_lead_doc.save(ignore_permissions=True)

            return original_lead_doc
        except Exception as e:
            local_lead_logger.error(f"保存线索失败 clue_id={clue_id}: {e}", exc_info=True)
            return None
    else:
        # 线索已存在，可以选择更新某些字段
        local_lead_logger.info(f"线索已存在 clue_id={clue_id}")
        return record


def ensure_valid_token(local_account: Document) -> tuple:
    """
    确保 Token 有效，如果即将过期则自动刷新

    :param local_account: Lead Domain for Local 文档
    :return: (success: bool, access_token: str, message: str)
    """
    if not local_account.access_token:
        local_lead_logger.error(f"Access Token 未配置，账户: {local_account.local_account_id}")
        return False, None, "Access Token 未配置，请先进行 OAuth 授权"

    access_token = local_account.get_password('access_token')

    # 检查 Token 是否即将过期（提前1小时刷新）
    if local_account.token_expires_at:
        expires_at = local_account.token_expires_at
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                local_lead_logger.error(f"解析 token_expires_at 失败: {e}")
                expires_at = None

        if expires_at:
            # 如果距离过期不足1小时，尝试刷新
            time_until_expiry = expires_at - datetime.now()
            hours_until_expiry = time_until_expiry.total_seconds() / 3600

            local_lead_logger.info(f"Token 状态检查，账户: {local_account.local_account_id}, "
                              f"过期时间: {expires_at}, 剩余: {hours_until_expiry:.2f} 小时")

            if time_until_expiry.total_seconds() < 3600:  # 1小时
                local_lead_logger.warning(f"Token 即将过期（剩余 {hours_until_expiry:.2f} 小时），"
                                     f"尝试自动刷新: {local_account.local_account_id}")

                if local_account.refresh_token:
                    refresh_result = _do_refresh_token(local_account)
                    if refresh_result.get("success"):
                        # 重新获取刷新后的 token
                        local_account.reload()
                        access_token = local_account.get_password('access_token')
                        local_lead_logger.info(f"Token 自动刷新成功: {local_account.local_account_id}")
                    else:
                        local_lead_logger.error(f"Token 自动刷新失败: {refresh_result.get('message')}")
                        return False, None, f"Token 已过期且自动刷新失败: {refresh_result.get('message')}"
                else:
                    local_lead_logger.error(f"Refresh Token 不存在，无法自动刷新: {local_account.local_account_id}")
                    return False, None, "Token 已过期，请重新进行 OAuth 授权"

    return True, access_token, "Token 有效"


def _do_refresh_token(local_account: Document) -> dict:
    """
    内部函数：执行 Token 刷新
    """
    try:
        settings = get_oceanengine_settings()

        if not local_account.refresh_token:
            local_lead_logger.warning(f"Refresh Token 不存在，账户: {local_account.local_account_id}")
            return {"success": False, "message": "Refresh Token 不存在"}

        refresh_token = local_account.get_password("refresh_token")
        local_lead_logger.info(f"开始刷新 Token，账户: {local_account.local_account_id}")

        payload = {
            "app_id": settings.app_id,
            "secret": settings.get_password("app_secret"),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        local_lead_logger.debug(f"Token 刷新请求: {OAUTH_REFRESH_URL}")
        response = requests.post(OAUTH_REFRESH_URL, json=payload, timeout=30)
        result = response.json()

        local_lead_logger.debug(f"Token 刷新响应: {result}")

        if result.get("code") == 0:
            data = result.get("data", {})
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 86400)
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            local_lead_logger.info(f"Token 刷新成功，expires_in={expires_in}, expires_at={expires_at}")

            local_account.access_token = new_access_token
            local_account.refresh_token = new_refresh_token
            local_account.token_expires_at = expires_at
            local_account.save(ignore_permissions=True)
            frappe.db.commit()

            return {"success": True, "message": "Token 刷新成功"}
        else:
            error_message = result.get('message', '刷新失败')
            error_code = result.get('code')
            local_lead_logger.error(f"Token 刷新失败，code={error_code}, message={error_message}")
            return {"success": False, "message": f"{error_message} (code: {error_code})"}

    except Exception as e:
        local_lead_logger.error(f"Token refresh exception: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_local_leads(local_account_id: str):
    """
    同步指定本地推账户的线索

    :param local_account_id: 本地账户ID
    :return: 同步结果消息
    """
    local_lead_logger.info(f"开始同步本地推线索: local_account_id={local_account_id}")
    try:
        # 获取本地推账户配置
        local_account = lead_tools.get_doc_or_none("Lead Domain for Local", {"local_account_id": local_account_id})
        
        if not local_account:
            return f"未找到本地推账户: {local_account_id}"
        
        # 自动检查并刷新 Token
        token_valid, access_token, token_msg = ensure_valid_token(local_account)
        if not token_valid:
            return token_msg
        
        # 计算时间范围
        sync_days = local_account.sync_days or 7
        end_time = datetime.now()
        start_time = end_time - timedelta(days=sync_days)
        
        start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 分页获取线索
        page = 1
        page_size = 100
        total_synced = 0
        total_skipped = 0
        
        while True:
            response = fetch_local_leads(
                access_token=access_token,
                local_account_ids=[int(local_account_id)],
                start_time=start_time_str,
                end_time=end_time_str,
                page=page,
                page_size=page_size
            )

            local_lead_logger.debug(f"API响应 (第{page}页): {response}")

            if not response:
                local_lead_logger.error(f"API请求失败，已同步 {total_synced} 条线索")
                return f"API请求失败，已同步 {total_synced} 条线索"

            if response.get('code') != 0:
                error_msg = response.get('message', '未知错误')
                error_code = response.get('code')
                local_lead_logger.error(f"API返回错误: code={error_code}, message={error_msg}, response={response}")
                return f"API返回错误: {error_msg}"

            data = response.get('data', {})
            leads_list = data.get('list', [])
            page_info = data.get('page_info', {})

            local_lead_logger.info(f"获取到 {len(leads_list)} 条线索，第 {page} 页，总共 {page_info.get('page_total', 1)} 页")

            if not leads_list:
                local_lead_logger.info(f"第 {page} 页无数据，结束同步")
                break

            # 处理每条线索
            for lead_data in leads_list:
                result = process_local_lead(lead_data, local_account)
                if result:
                    # 检查是否为新创建的线索
                    if hasattr(result, '_is_newly_created') and result._is_newly_created:
                        total_synced += 1
                    else:
                        total_skipped += 1
                else:
                    total_skipped += 1
            
            # 检查是否还有更多页
            page_total = page_info.get('page_total', 1)
            if page >= page_total:
                break
            
            page += 1
            
            # 防止请求过于频繁
            if page > 100:  # 最多100页，防止无限循环
                break
        
        # 更新最后同步时间
        local_account.last_sync_time = datetime.now()
        local_account.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return f"同步完成！新增 {total_synced} 条线索，跳过 {total_skipped} 条已存在线索"
    
    except Exception as e:
        frappe.db.rollback()
        local_lead_logger.error(f"同步失败: {e}")
        return f"同步失败: {str(e)}"


@frappe.whitelist()
def sync_all_local_accounts():
    """
    同步所有本地推账户的线索（供手动调用）
    """
    accounts = frappe.get_all("Lead Domain for Local", fields=["local_account_id"])
    
    results = []
    for account in accounts:
        result = sync_local_leads(account.local_account_id)
        results.append(f"{account.local_account_id}: {result}")
    
    return "\n".join(results)


def scheduled_sync_all_local_accounts():
    """
    定时任务：同步所有本地推账户的线索（增量同步）

    此函数由 hooks.py 中的 scheduler_events 调用
    每小时执行一次增量同步
    """
    local_lead_logger.info("开始执行定时同步本地推线索任务...")

    accounts = frappe.get_all("Lead Domain for Local",
                              filters={"access_token": ["is", "set"]},
                              fields=["local_account_id", "account_name"])

    if not accounts:
        local_lead_logger.info("没有配置 Access Token 的本地推账户")
        return

    total_synced = 0
    total_failed = 0

    for account in accounts:
        try:
            local_lead_logger.info(f"同步账户: {account.account_name or account.local_account_id}")
            result = incremental_sync_local_leads(account.local_account_id, hours=30*24)  # 同步最近30天

            if "同步完成" in result or "增量同步完成" in result:
                total_synced += 1
                local_lead_logger.info(f"账户 {account.local_account_id} 同步成功: {result}")
            else:
                total_failed += 1
                local_lead_logger.warning(f"账户 {account.local_account_id} 同步结果: {result}")

        except Exception as e:
            total_failed += 1
            local_lead_logger.error(f"账户 {account.local_account_id} 同步失败: {e}")

    local_lead_logger.info(f"定时同步任务完成: 成功 {total_synced} 个账户，失败 {total_failed} 个账户")


def scheduled_refresh_all_tokens():
    """
    定时任务：刷新所有本地推账户的Token

    此函数由 hooks.py 中的 scheduler_events 调用
    每6小时执行一次（通过cron: 0 */6 * * * *）
    确保Token永不过期
    """
    local_lead_logger.info("开始执行定时刷新Token任务...")

    accounts = frappe.get_all("Lead Domain for Local",
                              filters={"access_token": ["is", "set"]},
                              fields=["name", "local_account_id", "account_name"])

    if not accounts:
        local_lead_logger.info("没有配置 Access Token 的本地推账户")
        return

    total_refreshed = 0
    total_failed = 0

    for account_info in accounts:
        try:
            # 获取完整文档对象
            local_account = frappe.get_doc("Lead Domain for Local", account_info.name)

            local_lead_logger.info(f"检查Token状态: {account_info.account_name or account_info.local_account_id}")

            # 检查Token是否需要刷新
            if local_account.token_expires_at:
                expires_at = local_account.token_expires_at
                if isinstance(expires_at, str):
                    try:
                        expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        local_lead_logger.error(f"解析 token_expires_at 失败: {e}")
                        continue

                if expires_at:
                    time_until_expiry = expires_at - datetime.now()
                    hours_until_expiry = time_until_expiry.total_seconds() / 3600

                    local_lead_logger.info(f"Token状态: {account_info.local_account_id}, "
                                      f"过期时间: {expires_at}, 剩余: {hours_until_expiry:.2f} 小时")

                    # 如果剩余时间不足12小时，主动刷新Token
                    if hours_until_expiry < 12:
                        local_lead_logger.info(f"Token即将过期（剩余 {hours_until_expiry:.2f} 小时），"
                                          f"主动刷新: {account_info.local_account_id}")

                        if local_account.refresh_token:
                            refresh_result = _do_refresh_token(local_account)
                            if refresh_result.get("success"):
                                total_refreshed += 1
                                local_lead_logger.info(f"Token自动刷新成功: {account_info.local_account_id}")
                            else:
                                total_failed += 1
                                local_lead_logger.error(f"Token刷新失败: {refresh_result.get('message')}")
                        else:
                            local_lead_logger.warning(f"Refresh Token 不存在: {account_info.local_account_id}")
                    else:
                        local_lead_logger.info(f"Token状态良好，无需刷新: {account_info.local_account_id}")

        except Exception as e:
            total_failed += 1
            local_lead_logger.error(f"刷新Token失败 {account_info.local_account_id}: {e}", exc_info=True)

    local_lead_logger.info(f"定时刷新Token任务完成: 成功 {total_refreshed} 个账户，失败 {total_failed} 个账户")


def get_employee_account(local_account_id: str):
    """通过 local_account_id 找到 Lead Domain for Local 账号"""
    if not local_account_id:
        return None
    doc = lead_tools.get_doc_or_none("Lead Domain for Local", {"local_account_id": local_account_id})
    return doc


@frappe.whitelist()
def callback_clue_conversion(original_lead_name: str, event_type: str = "FORM_SUBMIT", 
                              convert_state: int = 1, pay_amount: int = None, remark: str = None):
    """
    回传线索转化数据到巨量平台
    
    :param original_lead_name: Original Leads 文档名称
    :param event_type: 事件类型 (FORM_SUBMIT/SMART_CALL/CONSULT/RESERVATION)
    :param convert_state: 转化状态 (1-有效, 2-无效, 3-待确认)
    :param pay_amount: 支付金额（分）
    :param remark: 备注
    :return: 回传结果
    """
    try:
        original_lead = frappe.get_doc("Original Leads", original_lead_name)

        if original_lead.source != 'Local':
            return {"success": False, "message": "该线索不是本地推来源"}

        if not original_lead.clue_id:
            return {"success": False, "message": "线索ID不存在"}

        # 获取本地推账户配置
        local_account = None
        if original_lead.employee_local_account:
            local_account = frappe.get_doc("Lead Domain for Local", original_lead.employee_local_account)
        
        if not local_account:
            return {"success": False, "message": "未找到关联的本地推账户"}
        
        access_token = local_account.get_password('access_token')
        if not access_token:
            return {"success": False, "message": "Access Token 未配置"}
        
        # 从原始JSON数据中获取 advertiser_id (local_account_id)
        advertiser_id = int(local_account.local_account_id)
        
        # 调用回传API
        occur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = clue_callback(
            access_token=access_token,
            advertiser_id=advertiser_id,
            clue_id=original_lead.clue_id,
            event_type=event_type,
            convert_state=convert_state,
            pay_amount=pay_amount,
            occur_time=occur_time,
            remark=remark
        )
        
        if response and response.get('code') == 0:
            local_lead_logger.info(f"线索回传成功: clue_id={original_lead.clue_id}")
            return {"success": True, "message": "线索回传成功"}
        else:
            error_msg = response.get('message', '未知错误') if response else 'API请求失败'
            local_lead_logger.error(f"线索回传失败: clue_id={original_lead.clue_id}, error={error_msg}")
            return {"success": False, "message": f"线索回传失败: {error_msg}"}
    
    except Exception as e:
        local_lead_logger.error(f"线索回传异常: {e}")
        return {"success": False, "message": f"线索回传异常: {str(e)}"}


@frappe.whitelist()
def batch_callback_clue_conversions(original_lead_names: str, event_type: str = "FORM_SUBMIT", convert_state: int = 1):
    """
    批量回传线索转化数据
    
    :param original_lead_names: Original Leads 名称列表 (JSON 字符串)
    :param event_type: 事件类型
    :param convert_state: 转化状态
    :return: 批量回传结果
    """
    try:
        lead_names = json.loads(original_lead_names) if isinstance(original_lead_names, str) else original_lead_names
        
        # 按账户分组
        account_clues = {}
        
        for lead_name in lead_names:
            original_lead = frappe.get_doc("Original Leads", lead_name)

            if original_lead.source != 'Local' or not original_lead.clue_id:
                continue

            if not original_lead.employee_local_account:
                continue
            
            account_id = original_lead.employee_local_account
            if account_id not in account_clues:
                account_clues[account_id] = []
            
            account_clues[account_id].append({
                "clue_id": original_lead.clue_id,
                "event_type": event_type,
                "convert_state": convert_state,
                "occur_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        results = {"success": 0, "failed": 0, "details": []}
        
        for account_id, clue_list in account_clues.items():
            local_account = frappe.get_doc("Lead Domain for Local", account_id)
            access_token = local_account.get_password('access_token')
            
            if not access_token:
                results["failed"] += len(clue_list)
                results["details"].append(f"账户 {account_id} 未配置 Access Token")
                continue
            
            advertiser_id = int(local_account.local_account_id)
            response = batch_clue_callback(access_token, advertiser_id, clue_list)
            
            if response and response.get('code') == 0:
                data = response.get('data', {})
                results["success"] += data.get('success_count', len(clue_list))
                results["failed"] += data.get('fail_count', 0)
            else:
                results["failed"] += len(clue_list)
                error_msg = response.get('message', '未知错误') if response else 'API请求失败'
                results["details"].append(f"账户 {account_id} 回传失败: {error_msg}")
        
        return results
    
    except Exception as e:
        local_lead_logger.error(f"批量线索回传异常: {e}")
        return {"success": 0, "failed": 0, "message": f"批量回传异常: {str(e)}"}


@frappe.whitelist()
def update_clue_follow(original_lead_name: str, follow_status: int, remark: str = None):
    """
    更新线索跟进状态到巨量平台
    
    :param original_lead_name: Original Leads 文档名称
    :param follow_status: 跟进状态 (1-未跟进, 2-跟进中, 3-已成交, 4-无效)
    :param remark: 备注
    :return: 更新结果
    """
    try:
        original_lead = frappe.get_doc("Original Leads", original_lead_name)

        if original_lead.source != 'Local':
            return {"success": False, "message": "该线索不是本地推来源"}

        if not original_lead.clue_id:
            return {"success": False, "message": "线索ID不存在"}

        local_account = None
        if original_lead.employee_local_account:
            local_account = frappe.get_doc("Lead Domain for Local", original_lead.employee_local_account)
        
        if not local_account:
            return {"success": False, "message": "未找到关联的本地推账户"}
        
        access_token = local_account.get_password('access_token')
        if not access_token:
            return {"success": False, "message": "Access Token 未配置"}
        
        advertiser_id = int(local_account.local_account_id)
        
        response = update_clue_follow_status(
            access_token=access_token,
            advertiser_id=advertiser_id,
            clue_id=original_lead.clue_id,
            follow_status=int(follow_status),
            remark=remark
        )
        
        if response and response.get('code') == 0:
            local_lead_logger.info(f"跟进状态更新成功: clue_id={original_lead.clue_id}")
            return {"success": True, "message": "跟进状态更新成功"}
        else:
            error_msg = response.get('message', '未知错误') if response else 'API请求失败'
            return {"success": False, "message": f"跟进状态更新失败: {error_msg}"}
    
    except Exception as e:
        local_lead_logger.error(f"跟进状态更新异常: {e}")
        return {"success": False, "message": f"更新异常: {str(e)}"}


@frappe.whitelist()
def incremental_sync_local_leads(local_account_id: str, hours: int = 24*30):
    """
    增量同步本地推线索（只同步指定小时内的新线索）
    
    :param local_account_id: 本地账户ID
    :param hours: 同步多少小时内的线索
    :return: 同步结果
    """
    try:
        local_account = lead_tools.get_doc_or_none("Lead Domain for Local", {"local_account_id": local_account_id})
        
        if not local_account:
            return f"未找到本地推账户: {local_account_id}"
        
        # 自动检查并刷新 Token
        token_valid, access_token, token_msg = ensure_valid_token(local_account)
        if not token_valid:
            return token_msg
        
        # 使用指定小时数
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        sync_mode = f"使用最近 {hours} 小时"

        start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(start_time, datetime) else str(start_time)
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        local_lead_logger.info(f"增量同步模式: {sync_mode}, 时间范围: {start_time_str} 到 {end_time_str}")
        
        page = 1
        page_size = 100
        total_synced = 0
        total_skipped = 0
        
        while True:
            local_lead_logger.info(f"增量同步请求第 {page} 页线索数据...")
            response = fetch_local_leads(
                access_token=access_token,
                local_account_ids=[int(local_account_id)],
                start_time=start_time_str,
                end_time=end_time_str,
                page=page,
                page_size=page_size
            )

            local_lead_logger.debug(f"API响应 (增量同步第{page}页): {response}")

            if not response:
                local_lead_logger.error(f"API请求失败，已同步 {total_synced} 条线索")
                return f"API请求失败，已同步 {total_synced} 条线索"

            if response.get('code') != 0:
                error_msg = response.get('message', '未知错误')
                error_code = response.get('code')
                local_lead_logger.error(f"API返回错误: code={error_code}, message={error_msg}, response={response}")
                return f"API返回错误: {error_msg}"

            data = response.get('data', {})
            leads_list = data.get('list', [])
            page_info = data.get('page_info', {})

            local_lead_logger.info(f"获取到 {len(leads_list)} 条线索，第 {page} 页，总共 {page_info.get('page_total', 1)} 页")

            if not leads_list:
                local_lead_logger.info(f"第 {page} 页无数据，结束增量同步")
                break

            for lead_data in leads_list:
                result = process_local_lead(lead_data, local_account)
                if result:
                    # 检查是否为新创建的线索
                    if hasattr(result, '_is_newly_created') and result._is_newly_created:
                        total_synced += 1
                    else:
                        total_skipped += 1
                else:
                    total_skipped += 1

            page_total = page_info.get('page_total', 1)
            if page >= page_total:
                break

            page += 1

            if page > 100:
                break

        local_account.last_sync_time = datetime.now()
        local_account.save(ignore_permissions=True)
        frappe.db.commit()

        # 根据同步结果返回不同的消息
        if total_synced == 0 and total_skipped == 0:
            return f"增量同步完成！时间范围 {start_time_str} 到 {end_time_str} 内没有新线索"
        else:
            return f"增量同步完成！新增 {total_synced} 条线索，跳过 {total_skipped} 条已存在线索"
    
    except Exception as e:
        frappe.db.rollback()
        local_lead_logger.error(f"增量同步失败: {e}")
        return f"增量同步失败: {str(e)}"


# ==================== OAuth 授权相关 ====================

def get_oceanengine_settings():
    """获取巨量引擎设置"""
    return frappe.get_single("OceanEngine Settings")


@frappe.whitelist()
def get_oauth_url(local_account_id: str = None):
    """
    生成 OAuth 授权 URL
    
    :param local_account_id: 可选，用于关联到特定的本地推账户
    :return: 授权 URL
    """
    settings = get_oceanengine_settings()
    
    if not settings.app_id:
        frappe.throw(_("请先在 OceanEngine Settings 中配置 App ID"))
    
    # 生成随机 state 用于验证
    state_data = {
        "random": secrets.token_hex(16),
        "local_account_id": local_account_id or "",
        "timestamp": datetime.now().isoformat()
    }
    state = frappe.generate_hash(json.dumps(state_data), 32)
    
    # 保存 state 用于后续验证
    settings.oauth_state = json.dumps({state: state_data})
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    
    # 获取完整的回调 URL
    site_url = frappe.utils.get_url()
    callback_url = f"{site_url}/api/method/erpnext_china.erpnext_china.doctype.lead_domain_for_local.lead_domain_for_local.oauth_callback"

    # 构建授权 URL
    # scope参数格式：整数数组，如 [10,14,200000032,100000005]
    # 权限说明：
    #   10 - 账号服务（一级权限）
    #   14 - 用户信息
    #   200000032 - 本地推账户管理
    #   100000005 - 本地推管理
    params = {
        "app_id": settings.app_id,
        "state": state,
        "scope": "[10,14,200000032,100000005]",  # 本地推相关权限（整数数组格式）
        "redirect_uri": callback_url,
        "rid": secrets.token_hex(8)  # 请求ID
    }

    auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return {
        "auth_url": auth_url,
        "state": state,
        "callback_url": callback_url
    }


@frappe.whitelist(allow_guest=True)
def oauth_callback(**kwargs):
    """
    OAuth 回调处理
    接收巨量开放平台的授权回调
    """
    auth_code = kwargs.get("auth_code")
    state = kwargs.get("state")
    
    local_lead_logger.info(f"OAuth callback received: auth_code={auth_code[:10] if auth_code else None}..., state={state}")
    
    if not auth_code:
        error_msg = kwargs.get("error_description", "授权失败")
        local_lead_logger.error(f"OAuth callback error: {error_msg}")
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = f"/app?oauth_error={error_msg}"
        return
    
    try:
        settings = get_oceanengine_settings()
        
        # 验证 state
        saved_states = json.loads(settings.oauth_state or "{}")
        if state not in saved_states:
            local_lead_logger.error("Invalid OAuth state")
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/app?oauth_error=Invalid state"
            return
        
        state_data = saved_states[state]
        local_account_id = state_data.get("local_account_id")
        
        # 用授权码换取 access_token
        token_data = exchange_code_for_token(auth_code, settings)
        
        if not token_data:
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/app?oauth_error=Token exchange failed"
            return
        
        # 保存 token 到对应的本地推账户
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 86400)  # 默认1天
        
        local_lead_logger.info(f"Token obtained successfully")
        
        # 计算过期时间
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # 如果指定了 local_account_id，更新该账户
        if local_account_id:
            update_local_account_token(local_account_id, access_token, refresh_token, expires_at)
            redirect_url = f"/app/lead-domain-for-local/{local_account_id}?oauth_success=1"
        else:
            # 获取已授权的账户列表（包含账户名称等详细信息）
            advertisers = get_authorized_advertisers(access_token)
            
            if advertisers:
                local_lead_logger.info(f"Found {len(advertisers)} authorized advertisers")
                
                # 为每个授权的账户创建或更新
                created_count = 0
                for adv in advertisers:
                    advertiser_id = str(adv.get("advertiser_id", ""))
                    advertiser_name = adv.get("advertiser_name", "")
                    account_role = adv.get("account_role", "")
                    is_valid = adv.get("is_valid", True)
                    
                    # 只处理有效的本地推相关账户
                    if is_valid and account_role in ["ADVERTISER", "PLATFORM_ROLE_LIFE", "PLATFORM_ROLE_LOCAL_AGENT"]:
                        create_or_update_local_account(
                            advertiser_id, 
                            access_token, 
                            refresh_token, 
                            expires_at,
                            advertiser_name,
                            account_role
                        )
                        created_count += 1
                
                local_lead_logger.info(f"Created/updated {created_count} local accounts")
            else:
                local_lead_logger.warning("No advertisers found in response")
            
            redirect_url = "/app/lead-domain-for-local?oauth_success=1"
        
        # 清除已使用的 state
        del saved_states[state]
        settings.oauth_state = json.dumps(saved_states)
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = redirect_url
        
    except Exception as e:
        local_lead_logger.error(f"OAuth callback exception: {e}")
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = f"/app?oauth_error={str(e)}"


def exchange_code_for_token(auth_code: str, settings) -> dict:
    """
    用授权码换取 access_token
    """
    try:
        payload = {
            "app_id": settings.app_id,
            "secret": settings.get_password("app_secret"),
            "grant_type": "auth_code",
            "auth_code": auth_code
        }
        
        response = requests.post(OAUTH_TOKEN_URL, json=payload, timeout=30)
        result = response.json()
        
        local_lead_logger.info(f"Token exchange response code: {result.get('code')}")
        
        if result.get("code") == 0:
            return result.get("data", {})
        else:
            local_lead_logger.error(f"Token exchange failed: {result.get('message')}")
            return None
            
    except Exception as e:
        local_lead_logger.error(f"Token exchange exception: {e}")
        return None


def get_authorized_advertisers(access_token: str) -> list:
    """
    获取已授权账户列表
    
    :param access_token: 访问令牌
    :return: 账户列表
    """
    try:
        headers = {
            "Access-Token": access_token,
        }
        params = {
            "access_token": access_token
        }
        
        response = requests.get(OAUTH_ADVERTISER_GET_URL, headers=headers, params=params, timeout=30)
        result = response.json()
        
        local_lead_logger.info(f"Get advertisers response code: {result.get('code')}")
        
        if result.get("code") == 0:
            data = result.get("data", {})
            advertiser_list = data.get("list", [])
            local_lead_logger.info(f"Found {len(advertiser_list)} authorized advertisers")
            return advertiser_list
        else:
            local_lead_logger.error(f"Get advertisers failed: {result.get('message')}")
            return []
            
    except Exception as e:
        local_lead_logger.error(f"Get advertisers exception: {e}")
        return []


def get_account_role_label(account_role: str) -> str:
    """
    获取账户角色的中文标签

    :param account_role: 账户角色代码
    :return: 中文标签
    """
    role_labels = {
        "ADVERTISER": "客户",
        "PLATFORM_ROLE_LIFE": "抖音来客",
        "PLATFORM_ROLE_LOCAL_AGENT": "本地推代理商",
        "PLATFORM_ROLE_AGENT": "代理商",
        "PLATFORM_ROLE_E_DOUYIN": "企业号",
        "DISTRIBUTOR": "分销商"
    }
    return role_labels.get(account_role, account_role or "未知角色")


@frappe.whitelist()
def fetch_authorized_accounts(local_account_id: str = None):
    """
    获取已授权的账户列表（供前端调用）
    
    :param local_account_id: 可选，指定使用哪个账户的 token
    :return: 账户列表
    """
    try:
        if local_account_id:
            doc = frappe.get_doc("Lead Domain for Local", {"local_account_id": local_account_id})
            access_token = doc.get_password("access_token")
        else:
            # 获取第一个有效的账户
            accounts = frappe.get_all("Lead Domain for Local", 
                                      filters={"access_token": ["is", "set"]},
                                      limit=1)
            if not accounts:
                return {"success": False, "message": "没有配置 Access Token 的账户"}
            doc = frappe.get_doc("Lead Domain for Local", accounts[0].name)
            access_token = doc.get_password("access_token")
        
        if not access_token:
            return {"success": False, "message": "Access Token 不存在"}
        
        advertisers = get_authorized_advertisers(access_token)

        # 返回所有有效账户（不再过滤，让用户选择）
        local_advertisers = []
        for adv in advertisers:
            account_role = adv.get("account_role", "")
            is_valid = adv.get("is_valid", True)

            # 只返回有效的账户
            if is_valid:
                local_advertisers.append({
                    "advertiser_id": adv.get("advertiser_id"),
                    "advertiser_name": adv.get("advertiser_name"),
                    "account_role": account_role,
                    "is_valid": is_valid,
                    "role_label": get_account_role_label(account_role)
                })

        # 统计本地推相关账户数量
        local_role_count = len([adv for adv in local_advertisers if adv.get("account_role") in ["ADVERTISER", "PLATFORM_ROLE_LIFE", "PLATFORM_ROLE_LOCAL_AGENT"]])

        return {
            "success": True,
            "data": local_advertisers,
            "total": len(advertisers),
            "local_count": len(local_advertisers),
            "local_role_count": local_role_count
        }
        
    except Exception as e:
        local_lead_logger.error(f"Fetch authorized accounts exception: {e}")
        return {"success": False, "message": str(e)}


def update_local_account_token(local_account_id: str, access_token: str, refresh_token: str, expires_at):
    """更新本地推账户的 token"""
    try:
        doc = frappe.get_doc("Lead Domain for Local", {"local_account_id": local_account_id})
        doc.access_token = access_token
        doc.refresh_token = refresh_token
        doc.token_expires_at = expires_at
        doc.save(ignore_permissions=True)
        local_lead_logger.info(f"Updated token for local account: {local_account_id}")
    except Exception as e:
        local_lead_logger.error(f"Failed to update local account token: {e}")


def create_or_update_local_account(advertiser_id: str, access_token: str, refresh_token: str, 
                                    expires_at, advertiser_name: str = None, account_role: str = None):
    """
    创建或更新本地推账户
    
    :param advertiser_id: 广告主ID
    :param access_token: 访问令牌
    :param refresh_token: 刷新令牌
    :param expires_at: 过期时间
    :param advertiser_name: 广告主名称
    :param account_role: 账户角色
    """
    try:
        existing = frappe.db.exists("Lead Domain for Local", {"local_account_id": advertiser_id})
        
        # 生成账户名称
        if advertiser_name:
            display_name = advertiser_name
        else:
            display_name = f"本地推账户-{advertiser_id}"
        
        # 添加账户类型标识
        role_labels = {
            "ADVERTISER": "客户",
            "PLATFORM_ROLE_LIFE": "抖音来客",
            "PLATFORM_ROLE_LOCAL_AGENT": "本地推代理商"
        }
        role_label = role_labels.get(account_role, "")
        if role_label:
            display_name = f"{display_name} ({role_label})"
        
        if existing:
            doc = frappe.get_doc("Lead Domain for Local", existing)
            doc.access_token = access_token
            doc.refresh_token = refresh_token
            doc.token_expires_at = expires_at
            # 更新账户名称（如果之前是默认名称）
            if doc.account_name and doc.account_name.startswith("本地推账户-"):
                doc.account_name = display_name
            doc.save(ignore_permissions=True)
            local_lead_logger.info(f"Updated existing local account: {advertiser_id} - {display_name}")
        else:
            doc = frappe.get_doc({
                "doctype": "Lead Domain for Local",
                "local_account_id": advertiser_id,
                "account_name": display_name,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": expires_at,
                "sync_days": 7
            })
            doc.insert(ignore_permissions=True)
            local_lead_logger.info(f"Created new local account: {advertiser_id} - {display_name}")
            
    except Exception as e:
        local_lead_logger.error(f"Failed to create/update local account: {e}")


@frappe.whitelist()
def refresh_access_token(local_account_id: str):
    """
    刷新 access_token
    
    :param local_account_id: 本地账户ID
    :return: 刷新结果
    """
    try:
        settings = get_oceanengine_settings()
        doc = frappe.get_doc("Lead Domain for Local", {"local_account_id": local_account_id})
        
        if not doc.refresh_token:
            return {"success": False, "message": "Refresh Token 不存在，请重新授权"}
        
        refresh_token = doc.get_password("refresh_token")
        
        payload = {
            "app_id": settings.app_id,
            "secret": settings.get_password("app_secret"),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(OAUTH_REFRESH_URL, json=payload, timeout=30)
        result = response.json()
        
        if result.get("code") == 0:
            data = result.get("data", {})
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 86400)
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            doc.access_token = new_access_token
            doc.refresh_token = new_refresh_token
            doc.token_expires_at = expires_at
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {"success": True, "message": "Token 刷新成功", "expires_at": str(expires_at)}
        else:
            return {"success": False, "message": f"刷新失败: {result.get('message')}"}
            
    except Exception as e:
        local_lead_logger.error(f"Token refresh exception: {e}")
        return {"success": False, "message": f"刷新异常: {str(e)}"}


# ==================== 工作台账户管理 ====================

def get_customer_center_advertisers(access_token: str, cc_account_id: str, page: int = 1, page_size: int = 100) -> dict:
    """
    获取工作台下的账户列表
    
    :param access_token: 访问令牌
    :param cc_account_id: 工作台账户ID
    :param page: 页码
    :param page_size: 每页数量
    :return: 账户列表和分页信息
    """
    try:
        headers = {
            "Access-Token": access_token,
        }
        params = {
            "cc_account_id": cc_account_id,
            "page": page,
            "page_size": page_size
        }
        
        response = requests.get(CUSTOMER_CENTER_ADVERTISER_LIST_URL, headers=headers, params=params, timeout=30)
        result = response.json()
        
        local_lead_logger.info(f"Get customer center advertisers response code: {result.get('code')}")
        
        if result.get("code") == 0:
            return result.get("data", {})
        else:
            local_lead_logger.error(f"Get customer center advertisers failed: {result.get('message')}")
            return {"list": [], "page_info": {}}
            
    except Exception as e:
        local_lead_logger.error(f"Get customer center advertisers exception: {e}")
        return {"list": [], "page_info": {}}


def get_all_customer_center_advertisers(access_token: str, cc_account_id: str) -> list:
    """
    获取工作台下的所有账户（自动分页）
    
    :param access_token: 访问令牌
    :param cc_account_id: 工作台账户ID
    :return: 完整账户列表
    """
    all_advertisers = []
    page = 1
    page_size = 100
    
    while True:
        data = get_customer_center_advertisers(access_token, cc_account_id, page, page_size)
        advertiser_list = data.get("list", [])
        page_info = data.get("page_info", {})
        
        all_advertisers.extend(advertiser_list)
        
        total_page = page_info.get("total_page", 1)
        if page >= total_page:
            break
        page += 1
    
    return all_advertisers


@frappe.whitelist()
def fetch_local_advertisers(cc_account_id: str, local_account_id: str = None):
    """
    获取工作台下的本地推账户列表（供前端调用）
    
    :param cc_account_id: 工作台账户ID（必填）
    :param local_account_id: 可选，指定使用哪个账户的 token
    :return: 本地推账户列表
    """
    try:
        if not cc_account_id:
            return {"success": False, "message": "请提供工作台账户ID (cc_account_id)"}
        
        if local_account_id:
            doc = frappe.get_doc("Lead Domain for Local", {"local_account_id": local_account_id})
            access_token = doc.get_password("access_token")
        else:
            # 获取第一个有效的账户
            accounts = frappe.get_all("Lead Domain for Local", 
                                      filters={"access_token": ["is", "set"]},
                                      limit=1)
            if not accounts:
                return {"success": False, "message": "没有配置 Access Token 的账户"}
            doc = frappe.get_doc("Lead Domain for Local", accounts[0].name)
            access_token = doc.get_password("access_token")
        
        if not access_token:
            return {"success": False, "message": "Access Token 不存在"}
        
        # 获取所有账户
        all_advertisers = get_all_customer_center_advertisers(access_token, cc_account_id)
        
        # 过滤和分类账户
        local_advertisers = []  # 本地推账户
        normal_advertisers = []  # 普通投放账户
        enterprise_accounts = []  # 企业号
        
        for adv in all_advertisers:
            advertiser_type = adv.get("advertiser_type", "")
            
            if advertiser_type == "LOCAL":
                # 本地推投放账号
                local_advertisers.append({
                    "advertiser_id": adv.get("advertiser_id"),
                    "advertiser_name": adv.get("advertiser_name"),
                    "advertiser_type": advertiser_type,
                    "type_label": "本地推"
                })
            elif advertiser_type == "NORMAL":
                # 普通投放账号
                normal_advertisers.append({
                    "advertiser_id": adv.get("advertiser_id"),
                    "advertiser_name": adv.get("advertiser_name"),
                    "advertiser_type": advertiser_type,
                    "type_label": "普通投放"
                })
            elif adv.get("e_douyin_id"):
                # 企业号
                enterprise_accounts.append({
                    "e_douyin_id": adv.get("e_douyin_id"),
                    "e_douyin_name": adv.get("e_douyin_name"),
                    "type_label": "企业号"
                })
            # DOU+ 类型账户不处理（不支持API操作）
        
        return {
            "success": True,
            "data": {
                "local": local_advertisers,
                "normal": normal_advertisers,
                "enterprise": enterprise_accounts
            },
            "summary": {
                "total": len(all_advertisers),
                "local_count": len(local_advertisers),
                "normal_count": len(normal_advertisers),
                "enterprise_count": len(enterprise_accounts)
            }
        }
        
    except Exception as e:
        local_lead_logger.error(f"Fetch local advertisers exception: {e}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def import_local_advertisers(cc_account_id: str, local_account_id: str = None):
    """
    从工作台导入本地推账户到系统
    
    :param cc_account_id: 工作台账户ID
    :param local_account_id: 可选，指定使用哪个账户的 token
    :return: 导入结果
    """
    try:
        if not cc_account_id:
            return {"success": False, "message": "请提供工作台账户ID (cc_account_id)"}
        
        if local_account_id:
            doc = frappe.get_doc("Lead Domain for Local", {"local_account_id": local_account_id})
            access_token = doc.get_password("access_token")
            refresh_token = doc.get_password("refresh_token") if doc.refresh_token else None
            expires_at = doc.token_expires_at
        else:
            # 获取第一个有效的账户
            accounts = frappe.get_all("Lead Domain for Local", 
                                      filters={"access_token": ["is", "set"]},
                                      limit=1)
            if not accounts:
                return {"success": False, "message": "没有配置 Access Token 的账户"}
            doc = frappe.get_doc("Lead Domain for Local", accounts[0].name)
            access_token = doc.get_password("access_token")
            refresh_token = doc.get_password("refresh_token") if doc.refresh_token else None
            expires_at = doc.token_expires_at
        
        if not access_token:
            return {"success": False, "message": "Access Token 不存在"}
        
        # 获取所有账户
        all_advertisers = get_all_customer_center_advertisers(access_token, cc_account_id)
        
        # 只导入本地推账户
        imported = 0
        updated = 0
        skipped = 0
        
        for adv in all_advertisers:
            advertiser_type = adv.get("advertiser_type", "")
            
            if advertiser_type == "LOCAL":
                advertiser_id = str(adv.get("advertiser_id", ""))
                advertiser_name = adv.get("advertiser_name", "")
                
                if not advertiser_id:
                    skipped += 1
                    continue
                
                existing = frappe.db.exists("Lead Domain for Local", {"local_account_id": advertiser_id})
                
                if existing:
                    # 更新已存在的账户名称
                    existing_doc = frappe.get_doc("Lead Domain for Local", existing)
                    if existing_doc.account_name != advertiser_name and advertiser_name:
                        existing_doc.account_name = advertiser_name
                        existing_doc.save(ignore_permissions=True)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # 创建新账户
                    new_doc = frappe.get_doc({
                        "doctype": "Lead Domain for Local",
                        "local_account_id": advertiser_id,
                        "account_name": advertiser_name or f"本地推账户-{advertiser_id}",
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_expires_at": expires_at,
                        "sync_days": 7
                    })
                    new_doc.insert(ignore_permissions=True)
                    imported += 1
                    local_lead_logger.info(f"Imported local account: {advertiser_id} - {advertiser_name}")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"导入完成：新增 {imported} 个，更新 {updated} 个，跳过 {skipped} 个",
            "imported": imported,
            "updated": updated,
            "skipped": skipped
        }
        
    except Exception as e:
        local_lead_logger.error(f"Import local advertisers exception: {e}")
        frappe.db.rollback()
        return {"success": False, "message": str(e)}
