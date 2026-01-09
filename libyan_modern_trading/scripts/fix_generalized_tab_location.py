import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🔗 Starting Fix: Moving Generalized Fields to Correct Tab ---")

    target_doctypes = [
        "Sales Order", "Purchase Order", "Sales Invoice", 
        "Purchase Invoice", "Customer", "Supplier", "Item"
    ]

    # 1. DELETE EXISTING MESSY FIELDS
    # We remove them first to ensure the new 'insert_after' logic applies cleanly.
    print("1. 🧹 Cleaning up misplaced fields...")
    for dt in target_doctypes:
        # Delete the specific custom fields we created
        frappe.db.sql("""
            DELETE FROM `tabCustom Field` 
            WHERE dt = %s AND fieldname LIKE 'custom_%%_generalized_%%'
        """, (dt,))
        
        # Also delete the data fields (txt, log, etc.)
        frappe.db.sql("""
            DELETE FROM `tabCustom Field` 
            WHERE dt = %s AND (
                fieldname LIKE 'custom_log_%%' OR 
                fieldname LIKE 'custom_txt_%%' OR 
                fieldname LIKE 'custom_dec_%%' OR 
                fieldname LIKE 'custom_int_%%'
            )
        """, (dt,))
    
    frappe.db.commit()

    # 2. DEFINE FIELDS WITH "DAISY CHAIN" LOGIC
    # This function ensures every field points to the one before it.
    
    def get_ordered_fields():
        fields = []
        
        # A. The Anchor (The Tab)
        # We start by inserting the Tab after 'connections_tab'
        last_field = "connections_tab"
        
        # 1. The Tab Break
        fields.append({
            "fieldname": "custom_tab_generalized_code",
            "label": "Generalized Code",
            "fieldtype": "Tab Break",
            "insert_after": last_field
        })
        last_field = "custom_tab_generalized_code"

        # 2. The Section Break
        fields.append({
            "fieldname": "custom_sec_generalized_code",
            "label": "",
            "fieldtype": "Section Break",
            "insert_after": last_field
        })
        last_field = "custom_sec_generalized_code"

        # 3. The 20 Data Fields (5 of each)
        # We define the order we want them to appear in the UI
        types_to_add = [
            ("txt", "TXT", "Data"),
            ("log", "LOG", "Check"),
            ("int", "INT", "Int"),
            ("dec", "DEC", "Float")
        ]

        for prefix, label_prefix, fieldtype in types_to_add:
            for i in range(1, 6): # 1 to 5
                fname = f"custom_{prefix}_{i}"
                fields.append({
                    "fieldname": fname,
                    "label": f"{label_prefix} {i}",
                    "fieldtype": fieldtype,
                    "allow_on_submit": 1,
                    "default": 0 if fieldtype in ["Check", "Int", "Float"] else None,
                    "insert_after": last_field  # <--- CRITICAL: Points to previous field
                })
                last_field = fname # Update anchor for next loop
        
        return fields

    # 3. CREATE FIELDS
    print("2. 🏗️  Re-creating fields with correct nesting...")
    new_fields_list = get_ordered_fields()
    
    # We collect all new fieldnames for the permission fix later
    all_fieldnames = [f["fieldname"] for f in new_fields_list]

    for dt in target_doctypes:
        print(f"   👉 Processing {dt}...")
        try:
            create_custom_fields({dt: new_fields_list})
            
            # 4. PERMISSION FIX (SQL)
            placeholders = ', '.join(['%s'] * len(all_fieldnames))
            sql = f"""
                UPDATE `tabCustom Field`
                SET is_system_generated = 0, read_only = 0
                WHERE dt = %s AND fieldname IN ({placeholders})
            """
            frappe.db.sql(sql, tuple([dt] + all_fieldnames))
            
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

    frappe.db.commit()
    print("--- ✅ DONE. Clearing Cache... ---")
    frappe.clear_cache()

