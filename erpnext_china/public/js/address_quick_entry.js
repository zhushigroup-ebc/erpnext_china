frappe.provide("frappe.ui.form");

frappe.ui.form.AddressQuickEntryForm = class CustomAddressQuickEntryForm extends (
    frappe.ui.form.QuickEntryForm
) {
    constructor(doctype, after_insert, init_callback, doc, force) {
        super(doctype, after_insert, init_callback, doc, force);
        this.skip_redirect_on_error = true;
    }

    render_dialog() {

        this.mandatory.forEach(element => {
            if (element.fieldname == "auto_fill") {
                element.click = () => {
                    const dialog = this.dialog;
                    const details = dialog.doc.details;
                    if (!details) return
                    frappe.call({
                        method: "erpnext_china.erpnext_china.doctype.aliyun_settings.aliyun_settings.get_address_details",
                        args: {
                            text: details
                        },
                        callback: function (r) {
                            const address = r.message;
                            dialog.set_value("address_title", details);
                            dialog.set_value("state", address['prov']);
                            dialog.set_value("city", address['city']);
                            const county = address['district'] || address['devzone'] || address['town'];
                            dialog.set_value("county", county);
                            dialog.set_value("address_line1", address['address']);
                            dialog.set_value("contact", address['contact']);
                            dialog.set_value("phone", address['phone']);
                            dialog.set_value("details", "");
                        }
                    });
                }
            }
        });

        super.render_dialog();
    }

    insert() {
        if (cur_frm) {
            this.dialog.doc["links"] = [{ "link_doctype": cur_frm.doctype, "link_name": cur_frm.docname }];
        }
        return super.insert();
    }

    open_form_if_not_list() {
        cur_frm.reload_doc();
    }
};
