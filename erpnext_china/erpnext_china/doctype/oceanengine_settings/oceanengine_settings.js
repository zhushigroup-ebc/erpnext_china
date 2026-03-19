// Copyright (c) 2026, Digitwise Ltd. and contributors
// For license information, please see license.txt

// frappe.ui.form.on("OceanEngine Settings", {
// 	refresh(frm) {

// 	},
// });
//
frappe.ui.form.on("OceanEngine Settings", {
	refresh(frm) {
		// 显示完整的回调 URL
		if (frm.doc.callback_url) {
			let site_url = frappe.boot.sitename || window.location.origin;
			let full_callback_url = site_url + frm.doc.callback_url;
			frm.set_df_property('callback_url', 'description', 
				`<strong>完整回调地址：</strong><br><code>${full_callback_url}</code><br><br>` +
				`请将此地址配置到巨量开放平台的应用回调URL中。<br><br>` +
				`<strong>提示：</strong>本地推相关功能请前往 <a href="/app/lead-domain-for-local">Lead Domain for Local</a> 进行操作。`
			);
		}
		
		// 添加跳转到本地推账户管理的按钮
		frm.add_custom_button(__('本地推账户管理'), function() {
			frappe.set_route('List', 'Lead Domain for Local');
		});
	},
});

