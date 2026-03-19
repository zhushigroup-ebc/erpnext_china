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
	},
});
