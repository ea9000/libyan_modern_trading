import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🎯 Starting Focused Repair for: CUSTOMER ---")
    doctype = "Customer"

    # ---------------------------------------------------------
    # STEP 1: DEEP CLEAN (Remove Broken Links)
    # ---------------------------------------------------------
    print("1. 🕵️‍♀️ Scanning for broken links...")
    
    # A. Check Custom Fields linking to missing DocTypes
    custom_links = frappe.get_all("Custom Field", 
        filters={"dt": doctype, "fieldtype": "Link"}, 
        fields=["name", "fieldname", "options", "label"]
    )
    
    for field in custom_links:
        # If options is set but the DocType doesn't exist
        if field.options and not frappe.db.exists("DocType", field.options):
            print(f"   🔥 Found Zombie Field: '{field.label}' ({field.fieldname}) -> Links to missing '{field.options}'")
            frappe.db.delete("Custom Field", field.name)
            
    # B. Check Property Setters (Standard fields that were broken)
    props = frappe.get_all("Property Setter", 
        filters={"doc_type": doctype, "property": "options"}, 
        fields=["name", "value", "field_name"]
    )
    for p in props:
        # Ignore standard types
        if p.value and p.value not in ["User", "Currency"] and not frappe.db.exists("DocType", p.value):
            print(f"   🔥 Found Broken Property Setter on '{p.field_name}' -> Links to missing '{p.value}'")
            frappe.db.delete("Property Setter", p.name)

    # C. Delete Old Generalized Fields (To fix the sort order)
    print("2. 🧹 Removing old/messy Generalized fields...")
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
    """, (doctype,))
    
    frappe.db.commit()

    # ---------------------------------------------------------
    # STEP 2: REBUILD (Daisy Chain Method)
    # ---------------------------------------------------------
    print("3. 🏗️  Installing clean fields...")

    fields = []
    # We use 'dashboard_tab' or 'details_tab' as anchor. 
    # 'connections_tab' sometimes doesn't exist on Customer in all versions.
    # Let's try inserting after the last standard tab usually found on Customer.
    last_field = "mobile_no" # A safe standard field in Customer to anchor near

    # 1. Tab Break
    fields.append({
        "fieldname": "custom_tab_generalized_code",
        "label": "Generalized Code",
        "fieldtype": "Tab Break",
        "insert_after": "standard_reply" # Try to put it at the end
    })
    last_field = "custom_tab_generalized_code"

    # 2. Section Break
    fields.append({
        "fieldname": "custom_sec_generalized_code",
        "label": "",
        "fieldtype": "Section Break",
        "insert_after": last_field
    })
    last_field = "custom_sec_generalized_code"

    # 3. The 20 Fields (Strict Order 1 -> 5)
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
            last_field = fname 

    try:
        create_custom_fields({doctype: fields})
        
        # SQL Fix Permissions
        all_fieldnames = [f["fieldname"] for f in fields]
        placeholders = ', '.join(['%s'] * len(all_fieldnames))
        sql = f"""
            UPDATE `tabCustom Field`
            SET is_system_generated = 0, read_only = 0
            WHERE dt = %s AND fieldname IN ({placeholders})
        """
        frappe.db.sql(sql, tuple([doctype] + all_fieldnames))
        
        frappe.db.commit()
        print(f"   ✅ SUCCESS: Customer table repaired and updated.")

    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")

    frappe.clear_cache()
