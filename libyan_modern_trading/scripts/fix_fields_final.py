import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- ☢️  STARTING 'NUCLEAR' FIX FOR SALES ORDER FIELDS ---")

    # 1. Define the specific fields to target
    target_fields = [
        "custom_tab_special_fields",
        "custom_special_discount_section",
        "custom_special_discount",
        "custom_special_discount_customer_pct",
        "custom_special_discount_agent_pct"
    ]

    # 2. FORCE DELETE (Custom Fields & Property Setters)
    # We must remove Property Setters too, as they often contain "read_only" locks.
    print("1. 🗑️  Deleting old fields and sticky properties...")
    
    for fname in target_fields:
        # Delete Custom Field
        frappe.db.delete("Custom Field", {"dt": "Sales Order", "fieldname": fname})
        # Delete Property Setters (The hidden locks)
        frappe.db.delete("Property Setter", {"doc_type": "Sales Order", "field_name": fname})

    frappe.db.commit()

    # 3. RE-DEFINE FIELDS (Clean definitions)
    print("2. ✨ Re-creating fields...")
    
    fields = {
        "Sales Order": [
            # Tab Break
            {
                "fieldname": "custom_tab_special_fields",
                "label": "Special Fields",
                "fieldtype": "Tab Break",
                "insert_after": "connections_tab",
                "is_system_generated": 0
            },
            # Section Break
            {
                "fieldname": "custom_special_discount_section",
                "label": "Special Discount Details",
                "fieldtype": "Section Break",
                "insert_after": "custom_tab_special_fields",
                "is_system_generated": 0
            },
            # Checkbox (Explicitly Read Only = 0)
            {
                "fieldname": "custom_special_discount",
                "label": "Special Discount",
                "fieldtype": "Check",
                "default": 0,
                "read_only": 0, 
                "insert_after": "custom_special_discount_section",
                "is_system_generated": 0
            },
            # Customer % (With Dependence)
            {
                "fieldname": "custom_special_discount_customer_pct",
                "label": "Special Discount – Customer",
                "fieldtype": "Percent",
                "read_only": 0,
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount",
                "is_system_generated": 0
            },
            # Agent % (With Dependence)
            {
                "fieldname": "custom_special_discount_agent_pct",
                "label": "Special Discount – Agent",
                "fieldtype": "Percent",
                "read_only": 0,
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount_customer_pct",
                "is_system_generated": 0
            }
        ]
    }

    create_custom_fields(fields)
    
    # 4. SQL FORCE UPDATE (The Safety Hammer)
    # This guarantees the database treats them as user-created fields (editable).
    print("3. 🔨 Forcing 'Standard' behavior via SQL...")
    
    placeholders = ', '.join(['%s'] * len(target_fields))
    sql = f"""
        UPDATE `tabCustom Field`
        SET is_system_generated = 0, module = NULL, read_only = 0
        WHERE dt = 'Sales Order' AND fieldname IN ({placeholders})
    """
    frappe.db.sql(sql, tuple(target_fields))
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Sales Order")
    
    print("--- ✅ DONE. Please Reload your Browser (Ctrl+Shift+R) ---")

