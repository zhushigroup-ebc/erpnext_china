import frappe

@frappe.whitelist()
def switch_theme(theme):
	if theme in ["Dark", "Light", "Automatic", "Ai Era"]:
		frappe.db.set_value("User", frappe.session.user, "desk_theme", theme)