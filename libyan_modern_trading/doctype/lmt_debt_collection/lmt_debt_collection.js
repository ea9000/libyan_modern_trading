frappe.ui.form.on('LMT Debt Collection', {
    refresh: function(frm) {
        // Filter customers to only show those managed by the current user
        frm.set_query('customer', function() {
            return {
                filters: {
                    'account_manager': frappe.session.user
                }
            };
        });
    },
    
    amount: function(frm) {
        // Trigger calculation on the UI side for instant feedback
        if (frm.doc.action_type === "ايداع" && frm.doc.amount > 0) {
            frm.trigger('calculate_ui_commission');
        }
    },

    customer: function(frm) {
        if (frm.doc.customer) {
            // Fetch customer details to show in the 'customer_details' field
            frappe.db.get_value('Customer', frm.doc.customer, ['address_line1', 'territory'], (r) => {
                let details = `الموقع: ${r.territory || ''}\nالعنوان: ${r.address_line1 || ''}`;
                frm.set_value('customer_details', details);
            });
            frm.trigger('calculate_ui_commission');
        }
    },

    calculate_ui_commission: function(frm) {
        // This mirrors the python logic for immediate UI feedback
        if (frm.doc.customer && frm.doc.amount) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Customer",
                    filters: { name: frm.doc.customer },
                    fieldname: "lmt_cust_type"
                },
                callback: function(r) {
                    let type = r.message.lmt_cust_type;
                    frappe.db.get_value('User', frappe.session.user, 
                        ['lmt_percentage_1', 'lmt_percentage_2'], (u) => {
                            let pct = (type === "Pharmacy") ? u.lmt_percentage_1 : u.lmt_percentage_2;
                            frm.set_value('agent_percentage', pct);
                            frm.set_value('agent_commission', (frm.doc.amount * pct) / 100);
                    });
                }
            });
        }
    }
});
