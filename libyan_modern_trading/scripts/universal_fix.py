import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🌍 Starting Universal Repair & Rebuild ---")

    target_doctypes = [
        "Sales Order", "Purchase Order", 
        "Sales Invoice", "Purchase Invoice", 
        "Customer", "Supplier", "Item"
    ]

    # STEP 1: KILL ZOMBIE FIELDS (The Hidden Errors)
    # We scan ALL target docs for fields linking to non-existent DocTypes.
    print("1. 🧟 Scanning for Zombie Fields (Broken Links)...")
    
    for dt in target_doctypes:
        # A. Check Custom Fields
        custom_links = frappe.get_all("Custom Field", 
            filters={"dt": dt, "fieldtype": "Link"}, 
            fields=["name", "fieldname", "options", "label"]
        )
        for field in custom_links:
            if field.options and not frappe.db.exists("DocType", field.options):
                print(f"   🔥 {dt}: Deleting broken field '{field.label}' (Links to missing '{field.options}')")
                frappe.db.delete("Custom Field", field.name)

        # B. Check Property Setters (Standard fields with broken options)
        props = frappe.get_all("Property Setter", 
            filters={"doc_type": dt, "property": "options"}, 
            fields=["name", "value", "field_name"]
        )
        for p in props:
            # Ignore standard types like 'User', 'Currency' etc.
            if p.value and p.value not in ["User", "Currency"] and not frappe.db.exists("DocType", p.value):
                print(f"   🔥 {dt}: Deleting broken Property Setter on '{p.field_name}' (Links to missing '{p.value}')")
                frappe.db.delete("Property Setter", p.name)

    frappe.db.commit()
    print("   ✅ Zombie fields eliminated.")

    # STEP 2: DELETE OLD GENERALIZED FIELDS (To fix sort order)
    print("2. 🧹 Clearing old Generalized Fields...")
    for dt in target_doctypes:
        frappe.db.sql("""
            DELETE FROM `tabCustom Field` 
            WHERE dt = %s AND (
                fieldname = 'custom_tab_generalized_code' OR
                fieldname = 'custom_sec_generalized_code' OR
                fieldname LIKE 'custom_txt_%%' OR 
                fieldname LIKE 'custom_log_%%' OR 
                fieldname LIKE 'custom_dec_%%' OR 
                fieldname LIKE 'custom_int_%%'
            )
        """, (dt,))
    frappe.db.commit()

    # STEP 3: RE-CREATE WITH STRICT SORTING
    print("3. 🏗️  Re-building fields (Correct Order 1->5)...")
    
    def get_fields():
        fields = []
        # Anchor: We attach to 'connections_tab' so it goes to the end
        last_field = "connections_tab"
        
        # 1. Tab
        fields.append({
            "fieldname": "custom_tab_generalized_code",
            "label": "Generalized Code",
            "fieldtype": "Tab Break",
            "insert_after": last_field
        })
        last_field = "custom_tab_generalized_code"

        # 2. Section
        fields.append({
            "fieldname": "custom_sec_generalized_code",
            "label": "",
            "fieldtype": "Section Break",
            "insert_after": last_field
        })
        last_field = "custom_sec_generalized_code"

        # 3. Data Fields (Strict Loop)
        # We explicitly add them one by one to ensure the "insert_after" chain is perfect
        types_to_add = [
            ("txt", "TXT", "Data"),
            ("log", "LOG", "Check"),
            ("int", "INT", "Int"),
            ("dec", "DEC", "Float")
        ]

        for prefix, label_prefix, fieldtype in types_to_add:
            for i in range(1, 6): # 1, 2, 3, 4, 5
                fname = f"custom_{prefix}_{i}"
                fields.append({
                    "fieldname": fname,
                    "label": f"{label_prefix} {i}",
                    "fieldtype": fieldtype,
                    "allow_on_submit": 1,
                    "default": 0 if fieldtype in ["Check", "Int", "Float"] else None,
                    "insert_after": last_field 
                })
                last_field = fname # This forces the next field to sit below this one
        
        return fields

    new_fields_list = get_fields()
    all_fieldnames = [f["fieldname"] for f in new_fields_list]

    for dt in target_doctypes:
        print(f"   👉 Processing {dt}...")
        try:
            create_custom_fields({dt: new_fields_list})
            
            # SQL Force Unlock
            placeholders = ', '.join(['%s'] * len(all_fieldnames))
            sql = f"""
                UPDATE `tabCustom Field`
                SET is_system_generated = 0, read_only = 0
                WHERE dt = %s AND fieldname IN ({placeholders})
            """
            frappe.db.sql(sql, tuple([dt] + all_fieldnames))
            
        except Exception as e:
            print(f"      ❌ FAILED on {dt}: {str(e)}")

    frappe.db.commit()
    print("--- ✅ DONE. Please Reload (Ctrl+Shift+R) ---")
    frappe.clear_cache()
