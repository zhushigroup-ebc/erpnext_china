// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Importer", {
	refresh: function (frm) {
		if(frm.is_new()) {
			frm.set_value('posting_date',frappe.datetime.add_days(frappe.datetime.month_start(), -1))
			frm.save()
		}
		else {
			this.attachments = frm.attachments.get_attachments()
			if(this.attachments?.length > 0) {
				frm.add_custom_button(
					__('Make Attendance Log'),
					() => {
						frappe.call({
							method:"make_attendance_log",
							doc:frm.doc,
							callback:function(r) {
								frm.reload_doc()
							}
						})
					})
			}
		}
		
	},
});
