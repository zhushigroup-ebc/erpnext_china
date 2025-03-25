// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("MBO Performance Evaluation", {

	refresh(frm) {
        if(["Pending", "月初目标确认-直属上级确认", "月初目标确认-被考核人确认"].includes(frm.doc.workflow_state)) {
            frm.events.set_childfield_read_only(frm, ["expected_goal", "weighting", "evaluation_criteria"], 0);
            frm.events.set_childfield_read_only(frm, ["actual_achievement", "score"], 1);
        } else {
            frm.events.set_childfield_read_only(frm, ["expected_goal", "weighting", "evaluation_criteria"], 1);
            frm.events.set_childfield_read_only(frm, ["actual_achievement", "score"], 0);
        }

        if(["公司确认", "被考核人确认", "已确认"].includes(frm.doc.workflow_state)) {
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", 1);
            frm.set_df_property("section_break_hgzw", "hidden", 0);
            frm.set_df_property("section_break_rsrt", "hidden", 0);
        } else {
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", 0);
            frm.set_df_property("section_break_hgzw", "hidden", 1);
            frm.set_df_property("section_break_rsrt", "hidden", 1);
        }

        if (frm.doc.workflow_records.length > 0) {
            frm.events.make_workflow_html(frm)
        }
	},
    set_childfield_read_only(frm, table_fields, value, table_row_name = null ) {
        table_fields.forEach(field=>{
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", value, frm.doc.name, field);
        })
    },
    make_workflow_html(frm) {
        let workflow_record_html_wrapper = frm.fields_dict['workflow_record_html'].wrapper;
        $(workflow_record_html_wrapper).empty();

        const data = {}
        frm.doc.workflow_records.reverse();
        frm.doc.workflow_records.forEach(item=>{
            if (item.workflow_state && item.workflow_state != "Pending") {
                data[item.workflow_state] = item;
            }
        })
        if(Object.keys(data).length == 0) return;
        
        let workflow_record_html = `
        <div style="overflow-x: auto;">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th style="min-width:120px;">环节</th>
                        <th style="min-width:120px;">时间</th>
                        <th style="min-width:120px;">签批人员</th>
                    </tr>
                </thead>
                <tbody>
            `
        let trs = '';
   
        Object.keys(data).forEach(key => {
            const item = data[key];
            let employee_name = item.employee_name ? item.employee_name: "";
            trs += `
                <tr>
                    <td>${key}</td>
                    <td>${frappe.format(item.approval_date, { fieldtype: "Datetime" })}</td>
                    <td>${employee_name}</td>
                </tr>
            `
        })
        workflow_record_html += trs;
        workflow_record_html += `
        </tbody>
        </table>
        </div>
        `
        $(workflow_record_html).appendTo(workflow_record_html_wrapper);
    }
});




frappe.ui.form.on("MBO Performance Evaluation Detail", {
	weighting(frm, cdt, cdn) {
        calculate_score(frm, cdt, cdn);
    },
    score(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if(row.score > row.weighting) {
            frappe.msgprint(`行${ row.idx } 得分${row.score}不可大于分值${row.weighting}！`)
            frappe.model.set_value(cdt, cdn, "score", row.weighting);
        }
        calculate_score(frm, cdt, cdn);
    }
});

function calculate_score(frm, cdt, cdn) {
    let total_score = 0;
    let final_score = 0;
    frm.doc.performance_evaluation_and_summary_form.forEach(item=>{
        total_score += item.weighting ? item.weighting : 0;
        final_score += item.score ? item.score : 0;
    })
    if(final_score > total_score) {
        frappe.throw("总得分不得大于总分值！")
    }
    frm.set_value("total_score", total_score);
    frm.set_value("final_score", final_score);

}