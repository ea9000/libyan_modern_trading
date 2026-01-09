import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🔧 Starting Repair: Converting to True Custom Fields ---")

    target_fields = [
        "custom_tab_special_fields",
        "custom_special_discount_section",
        "custom_special_discount",
        "custom_special_discount_customer_pct",
        "custom_special_discount_agent_pct"
    ]

    # STEP 1: DELETE EXISTING (Incorrect) FIELDS
    # We remove them completely to clear the "System Generated" cache
    for fname in target_fields:
        frappe.db.delete("Custom Field", {"dt": "Sales Order", "fieldname": fname})
    
    frappe.db.commit()
    print("   🗑️  Deleted old system-locked fields.")

    # STEP 2: DEFINE NEW FIELDS
    # We place the tab after 'connections_tab' so it appears at the end
    fields = {
        "Sales Order": [
            {
                "fieldname": "custom_tab_special_fields",
                "label": "Special Fields",
                "fieldtype": "Tab Break",
                "insert_after": "connections_tab"
            },
            {
                "fieldname": "custom_special_discount_section",
                "label": "Special Discount Details",
                "fieldtype": "Section Break",
                "insert_after": "custom_tab_special_fields",
                "collapsible": 0
            },
            {
                "fieldname": "custom_special_discount",
                "label": "Special Discount",
                "fieldtype": "Check",
                "default": 0,
                "insert_after": "custom_special_discount_section"
            },
            {
                "fieldname": "custom_special_discount_customer_pct",
                "label": "Special Discount – Customer",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount"
            },
            {
                "fieldname": "custom_special_discount_agent_pct",
                "label": "Special Discount – Agent",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount_customer_pct"
            }
        ]
    }

    # STEP 3: CREATE FIELDS
    create_custom_fields(fields)
    print("   ✨ Created new fields.")

    # STEP 4: THE CRITICAL FIX (SQL UPDATE)
    # This manually forces the database to forget these were created by a script/system
    # and treats them as if you created them manually in the UI.
    placeholders = ', '.join(['%s'] * len(target_fields))
    sql = f"""
        UPDATE `tabCustom Field`
        SET is_system_generated = 0, module = NULL
        WHERE dt = 'Sales Order' AND fieldname IN ({placeholders})
    """
    frappe.db.sql(sql, tuple(target_fields))
    frappe.db.commit()
    
    frappe.clear_cache(doctype="Sales Order")
    print("   ✅ FIXED: Fields are now standard Custom Fields (Editable & Safe).")

