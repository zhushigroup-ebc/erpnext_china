erpnext.utils.CRMNotes = class CRMNotes {
    constructor(opts) {
      $.extend(this, opts);
    }
    refresh() {
      var me = this;
      this.notes_wrapper.find(".notes-section").remove();
      let notes = this.frm.doc.notes || [];
      notes.sort(function(a, b) {
        return new Date(b.added_on) - new Date(a.added_on);
      });
      
      let notes_html = frappe.render_template("crm_notes", {
        notes
      });
      const wrapper = expand_notes_html(this.frm, $(notes_html))
      wrapper.appendTo(this.notes_wrapper);
      this.add_note();
      $(".notes-section").find(".edit-note-btn").on("click", function() {
        me.edit_note(this);
      });
      $(".notes-section").find(".delete-note-btn").on("click", function() {
        me.delete_note(this);
      });
    }
    add_note() {
      let me = this;
      let _add_note = () => {
        var d = new frappe.ui.Dialog({
          title: __("Add a Note"),
          fields: [
            {
              label: "Note",
              fieldname: "note",
              fieldtype: "Text", // 将Text Editor 修改为Text
              reqd: 1,
              enable_mentions: true
            }
          ],
          primary_action: function() {
            var data = d.get_values();
            frappe.call({
              method: "add_note",
              doc: me.frm.doc,
              args: {
                note: data.note
              },
              freeze: true,
              callback: function(r) {
                if (!r.exc) {
                  me.frm.refresh_field("notes");
                  me.refresh();
                }
                d.hide();
              }
            });
          },
          primary_action_label: __("Add")
        });
        d.show();
      };
      $(".new-note-btn").click(_add_note);
    }
    edit_note(edit_btn) {
      var me = this;
      let row = $(edit_btn).closest(".comment-content");
      let row_id = row.attr("name");
      let row_content = $(row).find(".content").html();
      if (row_content) {
        var d = new frappe.ui.Dialog({
          title: __("Edit Note"),
          fields: [
            {
              label: "Note",
              fieldname: "note",
              fieldtype: "Text",   // 将Text Editor 修改为Text
              default: row_content
            }
          ],
          primary_action: function() {
            var data = d.get_values();
            if(!data.note) {
                frappe.msgprint({
                    title: __('错误'),
                    indicator: 'red',
                    message: __('备注不能修改为空！')
                });
                return
            }
            frappe.call({
              method: "edit_note",
              doc: me.frm.doc,
              args: {
                note: data.note, // 这里必须有一个参数
                row_id
              },
              freeze: true,
              callback: function(r) {
                if (!r.exc) {
                  me.frm.refresh_field("notes");
                  me.refresh();
                  d.hide();
                }
              }
            });
          },
          primary_action_label: __("Done")
        });
        d.show();
      }
    }
    delete_note(delete_btn) {
      var me = this;
      let row_id = $(delete_btn).closest(".comment-content").attr("name");
      frappe.call({
        method: "delete_note",
        doc: me.frm.doc,
        args: {
          row_id
        },
        freeze: true,
        callback: function(r) {
          if (!r.exc) {
            me.frm.refresh_field("notes");
            me.refresh();
          }
        }
      });
    }
  };

function expand_notes_html(frm, wrapper) {
    let creationDatetime = moment(frm.doc.creation).format("YYYY-MM-DD HH:mm:ss");
    wrapper.find(".revisit-create-date").first().text("创建时间：" + creationDatetime);

    let revisitTimeBoxHtml = '';
    for (let i = 1; i <= 5; i++) {
        let times = '首次回访'
        let lastElementClass = ''
        let numBgClass = ''
        let preDatetime = creationDatetime;
        let expectedDatetime = creationDatetime;
        switch (i) {
            case 1:
                preDatetime = creationDatetime;
                expectedDatetime = addTohours(creationDatetime, 6)
                break;
            case 2:
                preDatetime = addTohours(creationDatetime, 6);
                expectedDatetime = addTohours(creationDatetime, 12);
                times = "第二次回访"
                break;
            case 3:
                preDatetime = addTohours(creationDatetime, 12);
                expectedDatetime = addTohours(creationDatetime, 18);
                times = "第三次回访"
                break;
            case 4:
                preDatetime = addTohours(creationDatetime, 18);
                expectedDatetime = addTohours(creationDatetime, 24);
                times = "第四次回访"
                break;
            case 5:
                preDatetime = addTohours(creationDatetime, 24);
                expectedDatetime = addTohours(creationDatetime, 48);
                times = "第五次回访"
                lastElementClass = 'last'
                break;
        }
        for(const note of frm.doc.notes) {
            if('销售反馈' == note.custom_note_type) {
                const code = getBgClass(note.added_on, preDatetime, expectedDatetime);
                if(code == 1) {
                    numBgClass = "success-bg-color";
                    break
                }
                if(code == 0) {
                    numBgClass = ''
                    break
                }
                numBgClass = 'expired-bg-color'
            }
        }
        
        const timeBoxItem = `<div class="time-box-item">
                <div class="time-title ${lastElementClass}">
                    <div class="time-num ${numBgClass}">${i}</div>
                </div>
                <div class="time-body">
                    <div class="times">${times}</div>
                    <p class="time-description">请在${expectedDatetime}前完成</p>
                </div>
            </div>`
        revisitTimeBoxHtml = revisitTimeBoxHtml + timeBoxItem
    }
    $(revisitTimeBoxHtml).appendTo(wrapper.find(".revisit-time-box").first())
    return wrapper
}

function addTohours(d, h, f = 'YYYY-MM-DD HH:mm:ss') {
    return moment(d).add(h, 'hours').format(f)
}

function getBgClass(targetDate, startDate, endDate) {
    const target = new Date(targetDate);
    const start = new Date(startDate);
    const end = new Date(endDate);

    // 如果反馈时间落入区间内，则success
    if (target >= start && target <= end) {
        return 1
    }

    // 如果当前时间还没到此区间的结束时间
    if (new Date() <= end) {
        return 0
    }
    
    // 其它情况都属于过期
    return -1
}