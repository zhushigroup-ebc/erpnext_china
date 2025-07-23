import frappe
from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
from frappe.share import add_docshare
from frappe.permissions import get_role_permissions
from frappe.utils import flt
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder

from erpnext_china.erpnext_china.overrides.controllers.taxes_and_totals import custom_calculate_taxes_and_totals

class CustomPurchaseOrder(PurchaseOrder):

	# 取消父类中对schedule_date的验证
	def validate_schedule_date(self):
		pass


	def calculate_taxes_and_totals(self):
		
		custom_calculate_taxes_and_totals(self)

		if self.doctype in (
			"Sales Order",
			"Delivery Note",
			"Sales Invoice",
			"POS Invoice",
		):
			self.calculate_commission()
			self.calculate_contribution()

def make_internal_sales_order(doc, method):
	if frappe.db.get_single_value("Selling Settings", "allow_generate_inter_company_transactions") and doc.is_internal_supplier:
		current_user = frappe.session.user
		frappe.set_user("Administrator")
		sales_order = make_inter_company_transaction('Purchase Order',doc.name,target_doc=None)

		validate_delivery_date(sales_order,doc)
		try:
			custom_set_missing_values(sales_order, doc)
			sales_order.save()
			sales_order.submit()
			sales_order.db_set('owner',doc.owner)
		except Exception as e:
			msg = _('Make Inter Company Sales Order Failed','zh')
			frappe.log_error(_('Make Inter Company Sales Order Failed'), frappe.get_traceback())
			frappe.set_user(current_user)
			frappe.msgprint(msg,alert=1)
			return

		role_permissions = get_role_permissions(frappe.get_meta(sales_order.doctype), current_user)
		add_docshare(
			sales_order.doctype, 
			sales_order.name, 
			doc.owner, 
			read=role_permissions.get('read'), 
			write=role_permissions.get('write'), 
			submit=role_permissions.get('submit'), 
			share=1, 
			flags={"ignore_share_permission": True}
		)
		
		frappe.set_user(current_user)

def validate_delivery_date(sales_order,purchase_order):
	for soi in sales_order.items:
		if not soi.delivery_date:
			poi_name = soi.purchase_order_item
			poi_schedule_date = [poi.schedule_date for poi in purchase_order.items if poi.name == poi_name]
			if len(poi_schedule_date) > 0:
				soi.delivery_date = poi_schedule_date[0]
			else:
				soi.delivery_date = purchase_order.schedule_date

def custom_set_missing_values(sales_order, purchase_order):
	sales_order.discount_amount = purchase_order.discount_amount
	sales_order.apply_discount_on = purchase_order.apply_discount_on
	# 设置成本中心
	default_cost_center = frappe.db.get_value('Company', sales_order.company, 'cost_center')
	for item in sales_order.items or []:
		item.cost_center = default_cost_center
	
	# 设置税项模板
	if purchase_order.taxes_and_charges:
		tax_category = frappe.db.get_value(
			"Sales Taxes and Charges Template", 
			purchase_order.taxes_and_charges, 
			"tax_category"
		)
		taxes_and_charges = frappe.db.get_all(
			"Sales Taxes and Charges Template", 
			filters={
				"company": sales_order.company,
				"tax_category": tax_category
			},
			pluck="name"
		)
		if taxes_and_charges and len(taxes_and_charges) > 0:
			sales_order.taxes_and_charges = taxes_and_charges[0]
	
	# 设置优惠后金额
	for item in sales_order.items or []:
		if item.purchase_order and item.purchase_order_item:
			po_item = frappe.db.get_value(
				"Purchase Order Item", 
				item.purchase_order_item, 
				["qty", "custom_after_distinct_amount_request"],
				as_dict=True 
			)
			item.custom_after_distinct__amount_request = flt(item.qty * po_item.custom_after_distinct_amount_request / po_item.qty, item.precision("amount"))
