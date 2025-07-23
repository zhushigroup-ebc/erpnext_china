import json
import frappe
from frappe.desk.search import search_widget

@frappe.whitelist()
def update_sorted_index(**kwargs):
	sorted_index = kwargs.get('sorted')
	if sorted_index:
		sorted_index = json.loads(sorted_index)
		for i in sorted_index:
			doc = frappe.get_doc("Lead Source", i.get('name'))
			doc.custom_sorted_index = int(i.get('index'))
			doc.save()


@frappe.whitelist()
def custom_source_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	根据custom_sorted_index升序排列
	"""
	results = search_widget(
		doctype,
		txt.strip(),
		searchfield=searchfield,
		page_length=page_len,
		filters=filters,
	)

	names = frappe.get_all("Lead Source", filters=[
		["name", 'in', [res[0] for res in results]]
    ], order_by="custom_sorted_index asc", pluck="name")
	return [(name, )for name in names]


