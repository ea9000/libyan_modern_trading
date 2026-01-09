import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🔄 Starting Final Master Re-Apply for All DocTypes ---")

    # The full list of documents to update
    target_doctypes = [
        "Sales Order", 
        "Purchase Order", 
        "Sales Invoice", 
        "Purchase Invoice", 
        "Customer", 
        "Supplier", 
        "Item"
    ]

    # ---------------------------------------------------------
    # 1. CLEANUP: Remove potentially partial/messy fields
    # ---------------------------------------------------------
    print("1. 🧹 Cleaning up old/partial Generalized fields...")
    
    for dt in target_doctypes:
        # Delete the Tab and Section breaks
        frappe.db.sql("""
            DELETE FROM `tabCustom Field` 
            WHERE dt = %s AND fieldname IN ('custom_tab_generalized_code', 'custom_sec_generalized_code')
        """, (dt,))
        
        # Delete the Data fields (txt, log, int, dec)
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

    # ---------------------------------------------------------
    # 2. DEFINE FIELDS (Daisy Chain Logic)
    # ---------------------------------------------------------
    def get_ordered_fields():
        fields = []
        last_field = "connections_tab"
        
        # A. Tab Break
        fields.append({
            "fieldname": "custom_tab_generalized_code",
            "label": "Generalized Code",
            "fieldtype": "Tab Break",
            "insert_after": last_field
        })
        last_field = "custom_tab_generalized_code"

        # B. Section Break
        fields.append({
            "fieldname": "custom_sec_generalized_code",
            "label": "",
            "fieldtype": "Section Break",
            "insert_after": last_field
        })
        last_field = "custom_sec_generalized_code"

        # C. The 20 Fields (5 of each)
        types_to_add = [
            ("txt", "TXT", "Data"),
            ("log", "LOG", "Check"),
            ("int", "INT", "Int"),
            ("dec", "DEC", "Float")
        ]

        for prefix, label_prefix, fieldtype in types_to_add:
            for i in range(1, 6):
                fname = f"custom_{prefix}_{i}"
                fields.append({
                    "fieldname": fname,
                    "label": f"{label_prefix} {i}",
                    "fieldtype": fieldtype,
                    "allow_on_submit": 1,
                    "default": 0 if fieldtype in ["Check", "Int", "Float"] else None,
                    "insert_after": last_field 
                })
                last_field = fname 
        
        return fields

    # ---------------------------------------------------------
    # 3. EXECUTE CREATION
    # ---------------------------------------------------------
    print("2. 🏗️  Creating clean fields on all DocTypes...")
    
    new_fields_list = get_ordered_fields()
    all_fieldnames = [f["fieldname"] for f in new_fields_list]

    for dt in target_doctypes:
        print(f"   👉 Processing {dt}...")
        try:
            create_custom_fields({dt: new_fields_list})
            
            # Permission Fix (SQL)
            placeholders = ', '.join(['%s'] * len(all_fieldnames))
            sql = f"""
                UPDATE `tabCustom Field`
                SET is_system_generated = 0, read_only = 0
                WHERE dt = %s AND fieldname IN ({placeholders})
            """
            frappe.db.sql(sql, tuple([dt] + all_fieldnames))
            
        except Exception as e:
            print(f"      ❌ Error on {dt}: {str(e)}")

    frappe.db.commit()
    print("--- ✅ DONE. Clearing Cache... ---")
    frappe.clear_cache()

