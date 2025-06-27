// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["考勤日报报表"] = {
	"filters": [
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            options: frappe.utils.range(2025, 2036),
            default: new Date().getFullYear(),
            reqd: 1
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: [
                {value: 1, label: "一月"},
                {value: 2, label: "二月"},
                {value: 3, label: "三月"},
                {value: 4, label: "四月"},
                {value: 5, label: "五月"},
                {value: 6, label: "六月"},
                {value: 7, label: "七月"},
                {value: 8, label: "八月"},
                {value: 9, label: "九月"},
                {value: 10, label: "十月"},
                {value: 11, label: "十一月"},
                {value: 12, label: "十二月"}
            ],
            default: new Date().getMonth() + 1,
            reqd: 1
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let department = frappe.query_report.get_filter_value("department")
                let filters = {};
                if (department) {
                    filters = {
                        department: ["in", [department]]
                    }
                }
                return {
                    filters
                };
            }
        },
        {
            fieldname: "result",
            label: __("Result"),
            fieldtype: "Data",
        },
	]
};
