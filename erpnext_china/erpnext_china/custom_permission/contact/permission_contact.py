import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree


def get_contacts(users, ptype):
	# 根据联系人下面关联的单据，如果用户有这个单据的权限，则对这个联系人也有权限
	# 当前仅判断关联单据为客户的
	contacts = []
	links = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "parentfield": "links", "parenttype": "Contact"}, fields=["*"])
	for link in links:
		for user in users:
			if frappe.has_permission("Customer", ptype=ptype, doc=link.link_name, user=user):
				contacts.append(link.parent)
	return contacts

def has_query_permission(user):
	if frappe.db.get_value('Has Role',{'parent':user,'role':'System Manager'}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	else:
		# 上级可以看到下级创建的联系人
		users = get_employee_tree(parent=user)
		users.append(user)
		
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"(tabContact.owner in {users_str})" 

		# 上级也可以看到下级拥有联系人关联客户单据权限的联系人
		# contacts = get_contacts(users, 'read')
		# if len(contacts) > 0:
		# 	contacts_str = str(tuple(contacts)).replace(',)',')')
		# 	conditions += f"or (tabContact.name in {contacts_str})"
	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager']]}):
		# 如果角色包含管理员，则看到全量
		return True
	else:
		users = get_employee_tree(parent=user)
		users.append(user)

		# contacts = get_contacts(users, 'write')
		if doc.owner in users:
			return True
		else:
			return False