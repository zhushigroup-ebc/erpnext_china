# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LogisticsAndCarrierCalculationTools(Document):
	def before_save(self):
		info = {'省' : self.city,
				'市' : self.state,
				'体积' : float(self.volumecubic_centimeter),
				'重量' : float(self.weightkg)*1000, 
				'快递公司' : self.logistics_and_carrier}

		method_code = frappe.db.get_value('Logistics And Carrier',filters = {'name':info['快递公司']},fieldname='freight_calculation_method')
		dynamic_code = {}
		exec(method_code,dynamic_code)
		func = dynamic_code['func']
		result = func(**info)
		self.calculation_result = result

@frappe.whitelist()
def get_freight():
	return '运费: 25.0, 时效: 1-2天'