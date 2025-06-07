frappe.ui.form.on('Sales Order', {
	onload(frm) {
        
		// 销售订单选择物料时，只选择已经定义的UOM
		frm.fields_dict['items'].grid.get_field('uom').get_query = function(doc, cdt, cdn){
			var row = locals[cdt][cdn];
			return {
				query:"erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
				filters: {'value':row.item_code, apply_on:"Item Code"},
			}
		};
	},
    custom_immediate_shipping_after_approval: function(frm) {
        if (!frm.doc.custom_immediate_shipping_after_approval) {
            frm.set_value("custom_printed_delivery_note", 0)
            frm.set_value("custom_printed_packing_list", 0)
        }
    },
    refresh(frm){
        
        // 设置子表字段的筛选条件
        // sales_common.js中会覆盖item_code 的查询条件，但是客户端脚本是在最后加载，因此写到客户端脚本中
		// frm.set_query("item_code", "items", ()=>{
        //     return {
        //         query: "erpnext.controllers.queries.item_query",
        //         filters: [
        //             ["Item", "disabled", "=", 0], // 只显示启用的项目
        //             ["Item", "has_variants", "=", 0], // 不显示变体项目
        //             ["Item", "is_sales_item", "=", 1], // 只显示销售项目
        //             ["Item", "item_group", "descendants of (inclusive)", "成品"], // 只显示成品组的项目
        //             // ["Item", "company", "in", [doc.company]] // 匹配主表的公司字段
        //             ["Item", "custom_is_oem_or_odm", "=", frm.doc.custom_order_type_for_product == "定制" ? 1 : 0], // 是否定制
        //         ]
        //     };
        // })

        frm.set_query("coupon_code", function(doc) {
            return {
                query:"erpnext_china_mdm.mdm.custom_form_script.sales_order.sales_order.query_coupon_code",
            }
        })

        // 添加按钮弹出dialog来筛选收付款凭证
        if(frappe.user.has_role('销售会计')) {
            frm.add_custom_button(
                __("Query Payment Entry"),
                () => frm.events.select_payment_entry(frm),
            );
        }
        // if(frm.doc.docstatus == 1 && !in_list(["Completed"],frm.doc.status)){
        //     frm.add_custom_button(
        //         __("Customer Payment Confirmation"),
        //         () => frm.events.create_customer_payment_confirmation(frm),
        //         __("Create")
        //     )
        // }

        // 添加按钮，写备注（custom_important_reminders）
        if (frappe.user.has_role('销售会计') || frappe.user.has_role('销售支持')){
            frm.add_custom_button(
                __("Add Important Reminders"),
                ()=> frm.events.add_custom_important_reminders(frm),
            )
        }
    },
    select_payment_entry(frm) {
        const handleFieldOnChange = ()=>{
            const query = {
                payment_type: dialog.get_value("payment_type"),
                company: dialog.get_value("company"),
                bank_account: dialog.get_value("bank_account"),
                party: dialog.get_value("party"),
                total_allocated_amount: dialog.get_value("total_allocated_amount"),
                unallocated_amount: dialog.get_value("unallocated_amount"),
                reference_no: dialog.get_value("reference_no"),
                reference_date: dialog.get_value("reference_date"),
                custom_payment_note: dialog.get_value("custom_payment_note"),
                include_submitted_doc: dialog.get_value("include_submitted_doc"),
            }
            frappe.call("erpnext_china.erpnext_china.custom_form_script.sales_order.sales_order.select_payment_entry", query).then(r=>{
                dialog.fields_dict.items.df.data.length = 0;
                dialog.get_secondary_btn().addClass("disabled");
                let draft_pe_num = 0;
                if (r.message && r.message.length > 0) {
                    r.message.forEach(pm => {
                        if(pm.docstatus == 0) draft_pe_num++
                        dialog.fields_dict.items.df.data.push({
                            name: pm.name,
                            bank_account: pm.bank_account,
                            total_allocated_amount: pm.total_allocated_amount,
                            unallocated_amount: pm.unallocated_amount,
                            reference_no: pm.reference_no,
                            reference_date: pm.reference_date,
                            custom_payment_note: pm.custom_payment_note,
                            docstatus: pm.docstatus == 0? `<span class="text-danger bold">${__('Draft')}</span>` : `<span class="text-success bold">${__('Submitted')}</span>`
                        });
                    });
                }
                if(draft_pe_num > 0 && frm.doc.docstatus == 1) {
                    dialog.get_secondary_btn().removeClass("disabled");
                }
                dialog.fields_dict.items.grid.refresh();
            })
        }
		const dialog = new frappe.ui.Dialog({
			title: __("查看收付款凭证"),
			size: "extra-large",
			fields: [
				{
					fieldname: "payment_type",
					fieldtype: "Select",
					label: __("收付款类型"),
					options: "Receive\nPay\nInternal Transfer",
					default: "Receive",
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "company",
					fieldtype: "Link",
					label: __("Company"),
					options: "Company",
					default: frm.doc.company,
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "bank_account",
					fieldtype: "Link",
					label: __("Bank Account"),
					options: "Bank Account",
                    get_query: () => {
						return {
							filters: [["Bank Account", "company", "=", dialog.get_value("company")]],
						};
					},
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "party",
					fieldtype: "Link",
					label: __("往来单位"),
					options: "Customer",
					default: frm.doc.customer,
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
                    fieldname: "include_submitted_doc",
                    fieldtype: "Check",
                    label: __("Include Submitted Doc"),
                    default: 0,
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
                },
				{ fieldtype: "Column Break" },
                {
					fieldname: "total_allocated_amount",
					fieldtype: "Data",
					label: __("已付金额(CNY)"),
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "unallocated_amount",
					fieldtype: "Data",
					label: __("未付金额(CNY)"),
                    default: frm.doc.grand_total - frm.doc.advance_paid,
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "reference_no",
					fieldtype: "Data",
					label: __("参考编号"),
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "reference_date",
					fieldtype: "Date",
					label: __("参考日期"),
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
                {
					fieldname: "custom_payment_note",
					fieldtype: "Data",
					label: __("转账备注"),
                    onchange: ()=>{
                        handleFieldOnChange()
                    }
				},
				{ fieldtype: "Section Break" },
				{
					fieldname: "items",
					fieldtype: "Table",
					label: __("收付款凭证"),
					allow_bulk_edit: false,
					cannot_add_rows: true,
					cannot_delete_rows: true,
                    description:`<span class="text-success">${__('Please Select Payment Entry Items And Click Matching Button To Match And Submit Entry')}</span>`,
					data: [],
					fields: [
						{
							fieldname: "name",
							fieldtype: "Link",
							label: __("Payment Entry"),
							options: "Payment Entry",
							read_only: 1,
							in_list_view: 1,
                            columns: 2,
						},
                        {
                            fieldname: "bank_account",
                            fieldtype: "Link",
                            label: __("Bank Account"),
                            options: "Bank Account",
                            read_only: 1,
							in_list_view: 1,
                        },
                        {
                            fieldname: "total_allocated_amount",
                            fieldtype: "Currency",
                            label: __("已付金额"),
                            read_only: 1,
							in_list_view: 1,
                            columns: 1,
                        },
                        {
                            fieldname: "unallocated_amount",
                            fieldtype: "Currency",
                            label: __("未付金额"),
                            read_only: 1,
							in_list_view: 1,
                            columns: 1,
                        },
                        {
                            fieldname: "reference_no",
                            fieldtype: "Data",
                            label: __("参考编号"),
                            read_only: 1,
							in_list_view: 1,
                        },
                        {
                            fieldname: "reference_date",
                            fieldtype: "Date",
                            label: __("参考日期"),
                            read_only: 1,
							in_list_view: 1,
                            columns: 1,
                        },
                        {
                            fieldname: "docstatus",
                            fieldtype: "Data",
                            label: __("Doc Status"),
                            read_only: 1,
							in_list_view: 1,
                            columns: 1,
                        },
                        {
                            fieldname: "custom_payment_note",
                            fieldtype: "Data",
                            label: __("转账备注"),
                            read_only: 1,
							in_list_view: 1,
                            // columns: 1,
                        },
					],
				},
			],
            primary_action_label: __("查询"),
			primary_action: () => {
                handleFieldOnChange();
                frappe.msgprint('查询完成')
			},
            secondary_action: () => {
                let selected_rows = dialog.fields_dict.items.grid.get_selected_children()
                if(selected_rows?.length > 0){
                    let pe_names = selected_rows.map(item=>{
                        return item.name
                    })
                    frappe.call({
                        method:"erpnext_china.erpnext_china.custom_form_script.sales_order.sales_order.matching_payment_entries",
                        args:{
                            docname: frm.doc.name,
                            payment_entries:pe_names
                        },
                        callback:(r)=>{
                            if(r.message){
                                let item_html = ''
                                r.message.matched_pe?.forEach((item)=>{
                                    item_html += `
                                        <tr>
                                            <td>
                                                <a href="${frappe.utils.get_form_link('Payment Entry',item.name)}" >${item.name}</a></td>
                                            <td class="text-right">${fmt_money(item.paid_amount)}</td>
                                            <td class="text-right">${fmt_money(item.unallocated_amount)}</td>
                                        </tr>`
                                })

                                let msg = `
                                    <h5 class="margin-top">付款单匹配情况</h5>
                                    <p>订单金额：${fmt_money(frm.doc.grand_total)}</p>
                                    <p>已匹配金额：${fmt_money(frm.doc.grand_total - r.message.unallocated_amount)}</p>
                                    <p class="text-danger">未分配金额：${fmt_money(r.message.unallocated_amount)}</p>
                                    <p>已匹配付款单信息如下：<p>
                                    <div>
                                        <table class="table table-bordered">
                                            <tr class="grid-heading-row text-center">
                                                <th width="33%">${__("Payment Entry")}</th>
                                                <th width="33%">${__('Paid Amount')}</th>
                                                <th width="33%">${__('Unallocated Amount')}</th>
                                            </tr>
                                            ${item_html}
                                        </table>
                                    </div>
                                `
                                if(r.message.matched_pe?.length > 0) {
                                    frappe.msgprint(msg);
                                }
                                handleFieldOnChange();
                            }
                        }
                    })
                }
            },
            secondary_action_label: __("Matching Payment Entry"),
        });
		dialog.fields_dict.items.grid.refresh();
		dialog.show();
        handleFieldOnChange();
	},

    create_customer_payment_confirmation(frm) {
        frm.sales_order = frm.docname
        frm.make_new("Customer Payment Confirmation")
    },

    add_custom_important_reminders(frm) {
        const dialog = new frappe.ui.Dialog({
			title: __("Add Important Reminders"),
			fields: [
				{
					fieldname: "important_reminders",
					fieldtype: "Text",
					label: __("Important Reminders"),
				},
				
			],
            primary_action_label: __("Save"),
			primary_action: () => {
                const custom_important_reminders = dialog.get_value("important_reminders");
                frappe.call('erpnext_china.erpnext_china.custom_form_script.sales_order.sales_order.set_custom_important_reminders', 
                    {"note": custom_important_reminders, "docname": frm.doc.name}
                )
                .then(r => {
                    frappe.msgprint("备注添加成功！")
                    console.log(r)
                })
                dialog.hide();
			},
        });
		dialog.show();
    }
})


frappe.ui.form.on("Sales Order Item", {
	item_code: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
        row.warehouse = ''
		if (frm.doc.delivery_date) {
			row.delivery_date = frm.doc.delivery_date;
			refresh_field("delivery_date", cdn, "items");
		} else {
			frm.script_manager.copy_from_first_row("items", row, ["delivery_date"]);
		}
        frappe.call("erpnext_china_mdm.mdm.custom_form_script.item.item.get_item_default_warehouse", {item_code: row.item_code, company: frm.doc.company}).then((r)=>{
            if(r.message) {
                row.warehouse = r.message;
                refresh_field("warehouse", cdn, "items");
            }
        })
	},
	delivery_date: function (frm, cdt, cdn) {
		if (!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "delivery_date");
		}
	}
});