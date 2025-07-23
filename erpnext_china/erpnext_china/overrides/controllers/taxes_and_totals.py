import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals


class custom_calculate_taxes_and_totals(calculate_taxes_and_totals):
    def apply_discount_amount(self):
        if self.doc.discount_amount:
            if not self.doc.apply_discount_on:
                frappe.throw(_("Please select Apply Discount On"))

            self.doc.base_discount_amount = flt(
                self.doc.discount_amount * self.doc.conversion_rate,
                self.doc.precision("base_discount_amount"),
            )

            if self.doc.apply_discount_on == "Grand Total" and self.doc.get("is_cash_or_non_trade_discount"):
                self.discount_amount_applied = True
                return

            total_for_discount_amount = self.get_total_for_discount_amount()
            net_total = 0
            expected_net_total = 0

            if total_for_discount_amount:
                # calculate item amount after Discount Amount
                for item in self._items:
                    # 重写折扣金额的分配方式，因为我们已经指定了优惠后金额，无需按比例进行分配
                    item_precision = item.precision("distributed_discount_amount")
                    distributed_amount = None
                    if self.doc.doctype == "Sales Order":
                        # 如果是内部订单行，必定有关联的采购订单行，所以必须确保采购订单行是正确的
                        if item.purchase_order and item.purchase_order_item:
                            po_item = frappe.db.get_value(
                                "Purchase Order Item", 
                                item.purchase_order_item, 
                                ["qty", "distributed_discount_amount"], 
                                as_dict=True
                            )
                            
                            distributed_amount = flt(item.qty * po_item.distributed_discount_amount / po_item.qty, item_precision)
                        # 如果是原始订单行，可以直接计算
                        else:
                            grand_total_fraction_for_current_item = self.doc.taxes[0].grand_total_fraction_for_current_item if self.doc.taxes else 1
                            distributed_amount = flt((item.amount - item.custom_after_distinct__amount_request) / grand_total_fraction_for_current_item, item_precision)
                    elif self.doc.doctype == "Delivery Note":
                        if item.against_sales_order and item.so_detail:
                            so_item = frappe.db.get_value(
                                "Sales Order Item", 
                                item.so_detail, 
                                ["qty", "distributed_discount_amount"], 
                                as_dict=True
                            )
                            distributed_amount = flt(item.qty * so_item.distributed_discount_amount / so_item.qty, item_precision)
                    # 采购订单行关联了源销售订单行，注意没有设置税项
                    elif self.doc.doctype == "Purchase Order":
                        if item.sales_order and item.sales_order_item:
                            so_item = frappe.db.get_value(
                                "Sales Order Item", 
                                item.sales_order_item, 
                                ["qty", "distributed_discount_amount"], 
                                as_dict=True
                            )
                            distributed_amount = flt(item.qty * so_item.distributed_discount_amount / so_item.qty, item_precision)
                    
                    if distributed_amount is None:
                        distributed_amount = (
						    flt(self.doc.discount_amount) * item.net_amount / total_for_discount_amount
					    )

                    adjusted_net_amount = item.net_amount - distributed_amount
                    expected_net_total += adjusted_net_amount
                    item.net_amount = flt(adjusted_net_amount, item.precision("net_amount"))
                    item.distributed_discount_amount = flt(
                        distributed_amount, item.precision("distributed_discount_amount")
                    )
                    net_total += item.net_amount

                    # discount amount rounding adjustment
                    if rounding_difference := flt(
                        expected_net_total - net_total, self.doc.precision("net_total")
                    ):
                        item.net_amount = flt(
                            item.net_amount + rounding_difference, item.precision("net_amount")
                        )
                        item.distributed_discount_amount = flt(
                            distributed_amount + rounding_difference,
                            item.precision("distributed_discount_amount"),
                        )
                        net_total += rounding_difference

                    item.net_rate = (
                        flt(item.net_amount / item.qty, item.precision("net_rate")) if item.qty else 0
                    )

                    self._set_in_company_currency(item, ["net_rate", "net_amount"])

                self.discount_amount_applied = True
                self._calculate()
        else:
            self.doc.base_discount_amount = 0