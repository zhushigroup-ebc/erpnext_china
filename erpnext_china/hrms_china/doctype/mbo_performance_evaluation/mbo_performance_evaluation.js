// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("MBO Performance Evaluation", {

    refresh(frm) {
        if (!frappe.user.has_role('System Manager')) {
            frm.set_df_property("employee", "read_only", 1);
        } else {
            frm.set_df_property("employee", "read_only", 0);
        }

        if (["Pending", "月初目标确认-直属上级确认", "月初目标确认-被考核人确认"].includes(frm.doc.workflow_state)) {
            frm.events.set_childfield_read_only(frm, ["expected_goal", "weighting", "evaluation_criteria"], 0);
            frm.events.set_childfield_read_only(frm, ["actual_achievement", "score"], 1);
        } else {
            frm.events.set_childfield_read_only(frm, ["expected_goal", "weighting", "evaluation_criteria"], 1);
            frm.events.set_childfield_read_only(frm, ["actual_achievement", "score"], 0);
        }

        if (["公司确认", "被考核人确认", "已确认"].includes(frm.doc.workflow_state)) {
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", 1);
            frm.set_df_property("section_break_hgzw", "hidden", 0);
            frm.set_df_property("section_break_rsrt", "hidden", 0);
        } else {
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", 0);
            frm.set_df_property("section_break_hgzw", "hidden", 1);
            frm.set_df_property("section_break_rsrt", "hidden", 1);
        }

        const items_wrapper = frm.fields_dict['performance_evaluation_and_summary_form'].wrapper;
        $(items_wrapper).find('.row-check').css({"height": "auto"});
        $(items_wrapper).find('.grid-static-col').css({"height": "auto", "max-height": "none"});
        $(items_wrapper).find(".row-index").css({"height": "auto"});
        $(items_wrapper).find(".ellipsis").css({"white-space": "normal"});

        frm.events.make_workflow_html(frm);
    },
    set_childfield_read_only(frm, table_fields, value, table_row_name = null) {
        table_fields.forEach(field => {
            frm.set_df_property("performance_evaluation_and_summary_form", "read_only", value, frm.doc.name, field);
        })
    },
    make_workflow_html(frm) {
        let workflow_record_html_wrapper = frm.fields_dict['workflow_record_html'].wrapper;
        $(workflow_record_html_wrapper).empty();

        frappe.call("erpnext_china.hrms_china.doctype.mbo_performance_evaluation.mbo_performance_evaluation.get_workflow_action",
            { "doc_name": frm.doc.name }).then((r) => {
                if (r.message) {
                    let actions = r.message.actions;

                    if (actions[0].status == "Open") {
                        let index = actions.findIndex(action => action.workflow_state == frm.doc.workflow_state);
                        if (index !== -1) {
                            actions = actions.slice(index + 1);
                        }
                    }

                    if (actions.length == 0) {
                        return;
                    }
                    actions.reverse();
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
                    actions.forEach(action => {
                        trs += `
                            <tr>
                                <td>${action.workflow_state == "Pending" ? "提交" : action.workflow_state}</td>
                                <td>${frappe.format(action.modified, { fieldtype: "Datetime" })}</td>
                                <td>${action.first_name}</td>
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
            })
    }
});




frappe.ui.form.on("MBO Performance Evaluation Detail", {
    weighting(frm, cdt, cdn) {
        calculate_score(frm, cdt, cdn);
    },
    score(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.score > row.weighting) {
            frappe.msgprint(`行${row.idx} 得分${row.score}不可大于分值${row.weighting}！`)
            frappe.model.set_value(cdt, cdn, "score", row.weighting);
        }
        calculate_score(frm, cdt, cdn);
    }
});

function calculate_score(frm, cdt, cdn) {
    let total_score = 0;
    let final_score = 0;
    frm.doc.performance_evaluation_and_summary_form.forEach(item => {
        total_score += item.weighting ? item.weighting : 0;
        final_score += item.score ? item.score : 0;
    })
    if (final_score > total_score) {
        frappe.throw("总得分不得大于总分值！")
    }
    frm.set_value("total_score", total_score);
    frm.set_value("final_score", final_score);

}