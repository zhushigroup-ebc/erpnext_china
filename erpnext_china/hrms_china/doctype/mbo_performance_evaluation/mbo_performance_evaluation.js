// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("MBO Performance Evaluation", {
	refresh(frm) {
        if (frm.doc.workflow_records.length > 0) {
            frm.events.make_workflow_html(frm)
        }
	},

    make_workflow_html(frm) {
        let workflow_record_html_wrapper = frm.fields_dict['workflow_record_html'].wrapper;
        $(workflow_record_html_wrapper).empty();

        const data = {}
        frm.doc.workflow_records.sort((a, b) => {
            const dateA = new Date(a.creation);
            const dateB = new Date(b.creation);
            return dateA - dateB; // 升序排序
          });
        frm.doc.workflow_records.reverse().forEach(item=>{
            if (item.workflow_state != "Pending") {
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