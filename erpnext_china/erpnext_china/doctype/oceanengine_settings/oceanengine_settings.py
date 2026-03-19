

# import frappe
from frappe.model.document import Document


class OceanEngineSettings(Document):
	pass


def get_settings():
    """获取巨量引擎设置"""
    return frappe.get_single("OceanEngine Settings")

