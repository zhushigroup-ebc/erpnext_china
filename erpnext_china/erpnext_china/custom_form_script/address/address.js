frappe.ui.form.on('Address', {
    state: function(frm) {
        // 当省字段发生变化时，获取省ID
        var state_id = frm.doc.state;

        if (state_id) {
            var filters = {
                'parent_territory': state_id
            };

            // 市字段应用过滤条件
            frm.set_query("city", function() {
                return {
                    filters: filters
                };
            });
        }
    },
    auto_fill: function(frm) {
        if(!frm.doc.details) return
        frappe.call({
            method: "erpnext_china.erpnext_china.doctype.aliyun_settings.aliyun_settings.get_address_details",
            args: {
                text: frm.doc.details
            },
            callback: function(r) {
                var address = r.message;
                frm.set_value('state', address['prov']);
                frm.set_value('city', address['city']);
                let county = address['district'] || address['devzone'] || address['town'];
                frm.set_value('county', county);
                frm.set_value('address_line1', address['address']);
                frm.set_value('contact', address['contact']);
                frm.set_value('phone', address['phone']);
                frm.set_value('details','')
            }
        });
    }
});