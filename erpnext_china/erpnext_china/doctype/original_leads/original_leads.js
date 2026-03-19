// Copyright (c) 2024, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Original Leads", {
	refresh(frm) {
        // 如果是销售，则隐藏
        const readOnly = frappe.user.has_role('销售')
        const fields = ['ad_attributes_section', 'section_break_ymsv', 'original_json_data_section']
        if (readOnly) {
            fields.forEach(field => {
                frm.fields_dict[field].df.hidden = true;
                frm.refresh_field(field);
            });
        }

        // 本地推线索专属功能按钮
        if (frm.doc.source === 'Local' && frm.doc.clue_id && !frm.is_new()) {
            // 线索回传按钮
            frm.add_custom_button(__('有效线索回传'), function() {
                frappe.confirm(
                    __('确定将此线索标记为"有效"并回传到巨量平台？'),
                    function() {
                        frappe.call({
                            method: 'erpnext_china.erpnext_china.doctype.lead_domain_for_local.lead_domain_for_local.callback_clue_conversion',
                            args: {
                                original_lead_name: frm.doc.name,
                                event_type: 'FORM_SUBMIT',
                                convert_state: 1
                            },
                            freeze: true,
                            freeze_message: __('正在回传线索...'),
                            callback: function(r) {
                                if (r.message) {
                                    if (r.message.success) {
                                        frappe.show_alert({message: r.message.message, indicator: 'green'});
                                    } else {
                                        frappe.msgprint({
                                            title: __('回传失败'),
                                            message: r.message.message,
                                            indicator: 'red'
                                        });
                                    }
                                }
                            }
                        });
                    }
                );
            }, __('本地推操作'));

            // 无效线索回传
            frm.add_custom_button(__('无效线索回传'), function() {
                frappe.prompt([
                    {
                        label: __('无效原因'),
                        fieldname: 'remark',
                        fieldtype: 'Small Text',
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'erpnext_china.erpnext_china.doctype.lead_domain_for_local.lead_domain_for_local.callback_clue_conversion',
                        args: {
                            original_lead_name: frm.doc.name,
                            event_type: 'FORM_SUBMIT',
                            convert_state: 2,
                            remark: values.remark
                        },
                        freeze: true,
                        freeze_message: __('正在回传线索...'),
                        callback: function(r) {
                            if (r.message) {
                                if (r.message.success) {
                                    frappe.show_alert({message: r.message.message, indicator: 'green'});
                                } else {
                                    frappe.msgprint({
                                        title: __('回传失败'),
                                        message: r.message.message,
                                        indicator: 'red'
                                    });
                                }
                            }
                        }
                    });
                }, __('标记为无效线索'), __('确认'));
            }, __('本地推操作'));

            // 更新跟进状态
            frm.add_custom_button(__('更新跟进状态'), function() {
                frappe.prompt([
                    {
                        label: __('跟进状态'),
                        fieldname: 'follow_status',
                        fieldtype: 'Select',
                        options: [
                            {value: 1, label: __('未跟进')},
                            {value: 2, label: __('跟进中')},
                            {value: 3, label: __('已成交')},
                            {value: 4, label: __('无效')}
                        ],
                        reqd: 1
                    },
                    {
                        label: __('备注'),
                        fieldname: 'remark',
                        fieldtype: 'Small Text'
                    }
                ], function(values) {
                    frappe.call({
                        method: 'erpnext_china.erpnext_china.doctype.lead_domain_for_local.lead_domain_for_local.update_clue_follow',
                        args: {
                            original_lead_name: frm.doc.name,
                            follow_status: values.follow_status,
                            remark: values.remark
                        },
                        freeze: true,
                        freeze_message: __('正在更新跟进状态...'),
                        callback: function(r) {
                            if (r.message) {
                                if (r.message.success) {
                                    frappe.show_alert({message: r.message.message, indicator: 'green'});
                                } else {
                                    frappe.msgprint({
                                        title: __('更新失败'),
                                        message: r.message.message,
                                        indicator: 'red'
                                    });
                                }
                            }
                        }
                    });
                }, __('更新跟进状态'), __('确认'));
            }, __('本地推操作'));
        }
	},
});
