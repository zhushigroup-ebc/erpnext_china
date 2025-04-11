# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document


class Kuaidi100Settings(Document):
	
    @staticmethod
    def get_state_message(code):
        code = frappe.utils.cstr(code)
        STATE_CODE_MESSAGE = {
            '1':	'揽收',
            '101':	'已下单',
            '102':	'待揽收',
            '103':	'已揽收',
            '0':	'在途',
            '1001':	'到达派件城市',
            '1002':	'干线',
            '1003':	'转递',
            '5'	:'派件',
            '501'	:'投柜或驿站',
            '3'	:'签收',
            '301':	'本人签收',
            '302':	'派件异常后签收',
            '303':	'代签',
            '304':	'投柜或站签收',
            '6':	'退回',
            '4':	'退签',
            '401':	'已销单',
            '14':	'拒签',
            '7':	'转投',
            '2':	'疑难',
            '201':	'超时未签收',
            '202':	'超时未更新',
            '203':	'拒收',
            '204':	'派件异常',
            '205':	'柜或驿站超时未取',
            '206':	'无法联系',
            '207':	'超区',
            '208':	'滞留',
            '209':	'破损',	
            '210':	'销单',	
            '8':	'清关',
            '10':	'待清关',	
            '11':	'清关中',	
            '12':	'已清关',	
            '13':	'清关异常',
            '14':	'拒签'
        }
        return STATE_CODE_MESSAGE.get(code, "未知")