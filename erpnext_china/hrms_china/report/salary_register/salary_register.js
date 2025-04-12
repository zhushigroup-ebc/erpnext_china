// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt


frappe.query_reports["Salary Register"] = {
	"filters": [
		{
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.month_start(), -1),
			reqd: 1,
			width: "100px",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			width: "100px",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			width: "100px",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			width: "100px",
		},
		{
			fieldname: "show_details",
			label: __("Show Details"),
			fieldtype: "Check",
			width: "100px",
			default:0,
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		// console.log(me.income_columns)
		value = default_formatter(value, row, column, data);
		if (column.id == 'attendance_rate' && data) {
			value = `<div class="progress" style="margin: 0px;">
				<div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="` + value.match(/(\d+)/)[0] +`" aria-valuemin="0" aria-valuemax="100" style="width: `+value.match(/(\d+)/)[0] + `%;" title="${__('Attendance Rate')}：`+value.match(/(\d+)/)[0] + `%">
				</div>
			</div>`;
		} else if (in_list(me.income_columns,column.id)) {
			return `<div class="text-success">` + value + `</div>`;
		} else if (in_list(me.deduction_columns,column.id)) {
			return `<div class="text-danger">` + value + `</div>`;
		}
		
		return value
		
		
	},
	onload: function (report) {
		me = this
		me.salary_components_list = []
		frappe.call({
			method:"erpnext_china.hrms_china.report.salary_register.salary_register.get_salary_components_list",
			// args:{},
			callback:(r)=>{
				
				me.salary_components_list = r.message
				me.income_columns = me.salary_components_list
					.filter(item => item.type === '收入')
					.map(item => item.salary_component);  
				me.deduction_columns = me.salary_components_list
					.filter(item => item.type === '扣除')
					.map(item => item.salary_component);  
				// console.log(me.salary_components_list,me.income_columns)
			}
		})
	}
};
