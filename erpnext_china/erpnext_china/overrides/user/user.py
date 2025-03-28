import frappe

@frappe.whitelist()
def switch_theme(theme):
	if theme == "Aiera":
		theme = "AIEra"
	if theme in ["Dark", "Light", "Automatic", "AIEra"]:
		frappe.db.set_value("User", frappe.session.user, "desk_theme", theme)