// Copyright (c) 2026, Digitwise Ltd. and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Lead Domain for Local", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2026, Digitwise Ltd. and contributors
// For license information, please see license.txt

const LOCAL_API_BASE = 'erpnext_china.erpnext_china.doctype.lead_domain_for_local.lead_domain_for_local';

frappe.ui.form.on("Lead Domain for Local", {
	refresh(frm) {
		// 检查是否有 OAuth 成功/失败的提示
		let urlParams = new URLSearchParams(window.location.search);
		if (urlParams.get('oauth_success')) {
			frappe.show_alert({message: __('OAuth 授权成功，Token 已自动获取！'), indicator: 'green'});
			// 清除 URL 参数
			window.history.replaceState({}, document.title, window.location.pathname);
		}
		
		if (!frm.is_new()) {
			// 显示 Token 状态
			if (frm.doc.token_expires_at) {
				let expires_at = frappe.datetime.str_to_obj(frm.doc.token_expires_at);
				let now = new Date();
				if (expires_at < now) {
					frm.dashboard.set_headline(__('Access Token 已过期，同步时将自动刷新（需要有效的 Refresh Token）'));
					frm.dashboard.set_headline_alert('orange');
				} else {
					let hours_left = Math.round((expires_at - now) / (1000 * 60 * 60));
					if (hours_left < 24) {
						frm.dashboard.set_headline(__(`Access Token 将在 ${hours_left} 小时后过期，同步时将自动刷新`));
					} else {
						frm.dashboard.set_headline(__(`Token 有效，${hours_left} 小时后过期`), 'green');
					}
				}
			} else if (!frm.doc.access_token) {
				frm.dashboard.set_headline(__('未配置 Access Token，请先进行 OAuth 授权'));
				frm.dashboard.set_headline_alert('red');
			}
			
			// ==================== Token 管理 ====================
			// OAuth 授权按钮（仅首次需要）
			frm.add_custom_button(__('OAuth 授权'), function() {
				frappe.call({
					method: `${LOCAL_API_BASE}.get_oauth_url`,
					args: {
						local_account_id: frm.doc.local_account_id
					},
					freeze: true,
					freeze_message: __('正在生成授权链接...'),
					callback: function(r) {
						if (r.message) {
							frappe.msgprint({
								title: __('OAuth 授权'),
								message: `
									<p><strong>说明：</strong>首次使用需要进行 OAuth 授权，授权成功后系统会自动保存 Token。</p>
									<p>之后同步线索时，系统会<strong>自动刷新 Token</strong>，无需再次授权。</p>
									<hr>
									<p><a href="${r.message.auth_url}" target="_blank" class="btn btn-primary">点击前往授权</a></p>
								`,
								indicator: 'blue'
							});
						}
					}
				});
			}, __('Token 管理'));
			
			// 手动刷新 Token 按钮
			if (frm.doc.refresh_token) {
				frm.add_custom_button(__('手动刷新 Token'), function() {
					frappe.call({
						method: `${LOCAL_API_BASE}.refresh_access_token`,
						args: {
							local_account_id: frm.doc.local_account_id
						},
						freeze: true,
						freeze_message: __('正在刷新 Token...'),
						callback: function(r) {
							if (r.message) {
								if (r.message.success) {
									frappe.show_alert({message: r.message.message, indicator: 'green'});
									frm.reload_doc();
								} else {
									frappe.msgprint({
										title: __('刷新失败'),
										message: r.message.message,
										indicator: 'red'
									});
								}
							}
						}
					});
				}, __('Token 管理'));
			}
			
			// ==================== 账户管理 ====================
			// 查看已授权账户按钮
			frm.add_custom_button(__('查看已授权账户'), function() {
				frappe.call({
					method: `${LOCAL_API_BASE}.fetch_authorized_accounts`,
					args: {
						local_account_id: frm.doc.local_account_id
					},
					freeze: true,
					freeze_message: __('正在获取已授权账户...'),
					callback: function(r) {
						if (r.message) {
							if (r.message.success) {
								let accounts = r.message.data || [];
								let total = r.message.total || 0;
								let local_count = r.message.local_count || 0;
								
								let html = `<p>共授权 <strong>${total}</strong> 个账户，其中 <strong>${local_count}</strong> 个可用于本地推</p><br>`;
								
								if (accounts.length > 0) {
									html += `<table class="table table-bordered">
										<thead>
											<tr>
												<th>账户ID</th>
												<th>账户名称</th>
												<th>账户类型</th>
												<th>状态</th>
											</tr>
										</thead>
										<tbody>`;
									
									let role_labels = {
										"ADVERTISER": "客户",
										"PLATFORM_ROLE_LIFE": "抖音来客",
										"PLATFORM_ROLE_LOCAL_AGENT": "本地推代理商"
									};
									
									accounts.forEach(function(acc) {
										let role = role_labels[acc.account_role] || acc.account_role;
										let status = acc.is_valid ? 
											'<span class="text-success">有效</span>' : 
											'<span class="text-danger">无效</span>';
										html += `<tr>
											<td>${acc.advertiser_id}</td>
											<td>${acc.advertiser_name || '-'}</td>
											<td>${role}</td>
											<td>${status}</td>
										</tr>`;
									});
									
									html += `</tbody></table>`;
								} else {
									html += '<p class="text-muted">没有找到可用于本地推的账户</p>';
								}
								
								frappe.msgprint({
									title: __('已授权账户列表'),
									message: html,
									indicator: 'blue'
								});
							} else {
								frappe.msgprint({
									title: __('获取失败'),
									message: r.message.message,
									indicator: 'red'
								});
							}
						}
					}
				});
			}, __('账户管理'));
			
			// 获取工作台账户按钮
			frm.add_custom_button(__('获取工作台账户'), function() {
				frappe.prompt([
					{
						label: __('工作台账户ID (cc_account_id)'),
						fieldname: 'cc_account_id',
						fieldtype: 'Data',
						reqd: 1,
						description: __('巨量引擎工作台的账户ID')
					}
				], function(values) {
					frappe.call({
						method: `${LOCAL_API_BASE}.fetch_local_advertisers`,
						args: {
							cc_account_id: values.cc_account_id,
							local_account_id: frm.doc.local_account_id
						},
						freeze: true,
						freeze_message: __('正在获取工作台账户列表...'),
						callback: function(r) {
							if (r.message) {
								if (r.message.success) {
									let data = r.message.data || {};
									let summary = r.message.summary || {};
									
									let html = `
										<div class="mb-3">
											<strong>账户统计：</strong>
											总计 ${summary.total} 个，
											本地推 ${summary.local_count} 个，
											普通投放 ${summary.normal_count} 个，
											企业号 ${summary.enterprise_count} 个
										</div>
									`;
									
									if (data.local && data.local.length > 0) {
										html += `
											<h5 class="text-primary">本地推账户 (${data.local.length})</h5>
											<table class="table table-bordered table-sm">
												<thead><tr><th>账户ID</th><th>账户名称</th></tr></thead>
												<tbody>`;
										data.local.forEach(function(acc) {
											html += `<tr><td>${acc.advertiser_id}</td><td>${acc.advertiser_name || '-'}</td></tr>`;
										});
										html += `</tbody></table>`;
									}
									
									if (data.normal && data.normal.length > 0) {
										html += `
											<h5 class="text-info">普通投放账户 (${data.normal.length})</h5>
											<table class="table table-bordered table-sm">
												<thead><tr><th>账户ID</th><th>账户名称</th></tr></thead>
												<tbody>`;
										data.normal.forEach(function(acc) {
											html += `<tr><td>${acc.advertiser_id}</td><td>${acc.advertiser_name || '-'}</td></tr>`;
										});
										html += `</tbody></table>`;
									}
									
									frappe.msgprint({
										title: __('工作台账户列表'),
										message: html,
										indicator: 'blue',
										wide: true
									});
								} else {
									frappe.msgprint({
										title: __('获取失败'),
										message: r.message.message,
										indicator: 'red'
									});
								}
							}
						}
					});
				}, __('输入工作台账户ID'), __('获取'));
			}, __('账户管理'));
			
			// 导入工作台账户按钮
			frm.add_custom_button(__('导入工作台账户'), function() {
				frappe.prompt([
					{
						label: __('工作台账户ID (cc_account_id)'),
						fieldname: 'cc_account_id',
						fieldtype: 'Data',
						reqd: 1,
						description: __('巨量引擎工作台的账户ID，将自动导入该工作台下的所有本地推账户')
					}
				], function(values) {
					frappe.confirm(
						__('确定要导入工作台下的所有本地推账户吗？已存在的账户将更新名称，新账户将继承当前账户的 Token。'),
						function() {
							frappe.call({
								method: `${LOCAL_API_BASE}.import_local_advertisers`,
								args: {
									cc_account_id: values.cc_account_id,
									local_account_id: frm.doc.local_account_id
								},
								freeze: true,
								freeze_message: __('正在导入本地推账户...'),
								callback: function(r) {
									if (r.message) {
										if (r.message.success) {
											frappe.msgprint({
												title: __('导入成功'),
												message: r.message.message,
												indicator: 'green'
											});
										} else {
											frappe.msgprint({
												title: __('导入失败'),
												message: r.message.message,
												indicator: 'red'
											});
										}
									}
								}
							});
						}
					);
				}, __('导入本地推账户'), __('导入'));
			}, __('账户管理'));
			
			// ==================== 同步线索 ====================
			// 全量同步按钮
			frm.add_custom_button(__('全量同步'), function() {
				frappe.confirm(
					__('全量同步将获取最近 ' + (frm.doc.sync_days || 7) + ' 天的所有线索，Token 过期时会自动刷新。是否继续？'),
					function() {
						frappe.call({
							method: `${LOCAL_API_BASE}.sync_local_leads`,
							args: {
								local_account_id: frm.doc.local_account_id
							},
							freeze: true,
							freeze_message: __('正在同步本地推线索（Token 过期时会自动刷新）...'),
							callback: function(r) {
								if (r.message) {
									let indicator = r.message.includes('失败') || r.message.includes('错误') ? 'red' : 'green';
									frappe.msgprint({
										title: __('同步结果'),
										message: r.message,
										indicator: indicator
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}, __('同步线索'));
			
			// 增量同步按钮
			frm.add_custom_button(__('增量同步'), function() {
				frappe.call({
					method: `${LOCAL_API_BASE}.incremental_sync_local_leads`,
					args: {
						local_account_id: frm.doc.local_account_id,
						hours: 24*30
					},
					freeze: true,
					freeze_message: __('正在增量同步线索（Token 过期时会自动刷新）...'),
					callback: function(r) {
						if (r.message) {
							let indicator = r.message.includes('失败') || r.message.includes('错误') ? 'red' : 'green';
							frappe.msgprint({
								title: __('同步结果'),
								message: r.message,
								indicator: indicator
							});
							frm.reload_doc();
						}
					}
				});
			}, __('同步线索'));
		}
	},
});

