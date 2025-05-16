import frappe
from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree


def has_query_permission(user):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','HR Manager']]}):
		conditions = ''
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"`tabMBO Performance Evaluation`.`user` in {users_str} or `tabMBO Performance Evaluation`.`owner` in {users_str}"
		
	return conditions

def has_permission(doc, user, permission_type=None):
	user_roles = frappe.get_roles(user)
	if any(role in user_roles for role in ['System Manager','HR Manager']):
		return True
	else:
		if doc.user == user or doc.owner == user:
			return True
		elif doc.user in get_employee_tree(parent=user):
			return True
		else:
			return False