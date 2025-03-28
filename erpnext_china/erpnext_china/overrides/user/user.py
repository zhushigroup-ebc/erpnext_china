import frappe

@frappe.whitelist()
def switch_theme(theme):
	frappe.db.set_value("User", frappe.session.user, "desk_theme", theme)