import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🛠️  Starting Fix: Converting fields to Custom ---")

    # List of fieldnames we want to fix
    target_fields = [
        "custom_tab_special_fields",
        "custom_special_discount_section",
        "custom_special_discount",
        "custom_special_discount_customer_pct",
        "custom_special_discount_agent_pct"
    ]

    # STEP 1: FORCE DELETE EXISTING INCORRECT FIELDS
    # We delete them from the "Custom Field" table to remove the "System Generated" lock.
    print(f"🗑️  Deleting {len(target_fields)} potential system fields to avoid conflicts...")
    
    for fname in target_fields:
        if frappe.db.exists("Custom Field", {"dt": "Sales Order", "fieldname": fname}):
            frappe.db.delete("Custom Field", {"dt": "Sales Order", "fieldname": fname})
            print(f"   - Deleted old field: {fname}")

    # Commit the deletion before re-creating
    frappe.db.commit()

    # STEP 2: RE-CREATE AS PURE CUSTOM FIELDS
    # Using create_custom_fields ensures they are flagged as 'is_system_generated=0'
    print("✨ Re-creating fields as valid Custom Fields...")
    
    fields = {
        "Sales Order": [
            # 1. New Tab: Special Fields 
            # (Insert after 'Connections' tab usually ensures it sits at the end)
            {
                "fieldname": "custom_tab_special_fields",
                "label": "Special Fields",
                "fieldtype": "Tab Break", 
                "insert_after": "connections_tab" 
            },
            # 2. Section Break: Special Discount Details
            {
                "fieldname": "custom_special_discount_section",
                "label": "Special Discount Details",
                "fieldtype": "Section Break",
                "insert_after": "custom_tab_special_fields",
                "collapsible": 0
            },
            # 3. Special Discount (Checkbox)
            {
                "fieldname": "custom_special_discount",
                "label": "Special Discount",
                "fieldtype": "Check",
                "default": 0,
                "insert_after": "custom_special_discount_section"
            },
            # 4. Customer %
            {
                "fieldname": "custom_special_discount_customer_pct",
                "label": "Special Discount – Customer",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount"
            },
            # 5. Agent %
            {
                "fieldname": "custom_special_discount_agent_pct",
                "label": "Special Discount – Agent",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount_customer_pct"
            }
        ]
    }

    create_custom_fields(fields)
    
    # Explicitly ensure they are NOT system generated (safety net)
    for fname in target_fields:
        frappe.db.set_value("Custom Field", {"dt": "Sales Order", "fieldname": fname}, "is_system_generated", 0)

    frappe.db.commit()
    print("✅ Success: Fields are now fully Custom and safe from updates.")

