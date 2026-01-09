import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    DOCTYPE = "Warehouse"
    print(f"--- 🐞 Debug Mode: Repairing {DOCTYPE} ---")

    # 1. VERIFY DOCTYPE EXISTS
    if not frappe.db.exists("DocType", DOCTYPE):
        print(f"❌ Critical Error: DocType {DOCTYPE} not found!")
        return

    # 2. CLEANUP (ZOMBIES)
    print("1. 🧹 Scanning for broken links (Zombies)...")
    zombies = frappe.db.sql(f"""
        SELECT name, fieldname, options, label FROM `tabCustom Field`
        WHERE dt = '{DOCTYPE}' AND fieldtype = 'Link'
    """, as_dict=True)
    
    for z in zombies:
        if z.options and not frappe.db.exists("DocType", z.options):
            print(f"   🔥 Deleting Zombie Field: '{z.label}' ({z.fieldname}) -> Links to missing '{z.options}'")
            frappe.db.delete("Custom Field", z.name)
    frappe.db.commit()

    # 3. CLEANUP (OLD GENERALIZED FIELDS)
    print("2. 🗑️  Removing old Generalized Fields...")
    frappe.db.sql(f"""
        DELETE FROM `tabCustom Field`
        WHERE dt = '{DOCTYPE}' AND (
            fieldname = 'custom_tab_generalized_code' OR
            fieldname = 'custom_sec_generalized_code' OR
            fieldname LIKE 'custom_txt_%%' OR 
            fieldname LIKE 'custom_log_%%' OR
            fieldname LIKE 'custom_int_%%' OR 
            fieldname LIKE 'custom_dec_%%'
        )
    """)
    frappe.db.commit()

    # 4. FIND ANCHOR (The smart part)
    # We look for the last 'Standard' field to insert our tab after.
    # This prevents the fields from floating to the top if specific fields are missing.
    last_field = frappe.db.get_value("DocField", {"parent": DOCTYPE}, "fieldname", order_by="idx desc")
    
    if not last_field:
        last_field = "item_name" # Fallback safe bet for Item
    
    print(f"3. ⚓ Anchor Point found: Inserting new tab after '{last_field}'")

    # 5. DEFINE FIELDS
    fields_to_create = []
    
    # A. Tab Break
    fields_to_create.append({
        "fieldname": "custom_tab_generalized_code",
        "label": "Generalized Code",
        "fieldtype": "Tab Break",
        "insert_after": last_field
    })
    previous = "custom_tab_generalized_code"

    # B. Section Break
    fields_to_create.append({
        "fieldname": "custom_sec_generalized_code",
        "label": "",
        "fieldtype": "Section Break",
        "insert_after": previous
    })
    previous = "custom_sec_generalized_code"

    # C. Data Fields (1-5 Loop)
    types = [("txt", "TXT", "Data"), ("log", "LOG", "Check"), ("int", "INT", "Int"), ("dec", "DEC", "Float")]
    
    for prefix, label, ftype in types:
        for i in range(1, 6):
            fname = f"custom_{prefix}_{i}"
            fields_to_create.append({
                "fieldname": fname,
                "label": f"{label} {i}",
                "fieldtype": ftype,
                "insert_after": previous,
                "allow_on_submit": 1,
                "default": 0 if ftype in ["Check", "Int", "Float"] else None
            })
            previous = fname

    # 6. CREATE
    print(f"4. 🏗️  Attempting to create {len(fields_to_create)} fields...")
    try:
        create_custom_fields({DOCTYPE: fields_to_create})
        frappe.db.commit()
    except Exception as e:
        print(f"   ❌ Creation Failed: {str(e)}")
        return

    # 7. VERIFY
    print("5. 🕵️‍♀️ Verifying in Database...")
    
    # We query the DB directly to see if the records exist
    created_fields = frappe.db.sql(f"""
        SELECT fieldname, label, insert_after FROM `tabCustom Field`
        WHERE dt = '{DOCTYPE}' AND fieldname LIKE 'custom_%%_generalized_%%'
        OR (dt = '{DOCTYPE}' AND fieldname LIKE 'custom_txt_1')
    """, as_dict=True)

    if len(created_fields) > 0:
        print(f"   ✅ SUCCESS! Query found the following fields in DB:")
        for f in created_fields:
            print(f"      - {f.fieldname} (After: {f.insert_after})")
    else:
        print("   ❌ FAILURE! The script finished, but the Database returns 0 fields found.")

    # 8. PERMISSION UNLOCK
    print("6. 🔓 Unlocking Permissions...")
    frappe.db.sql(f"UPDATE `tabCustom Field` SET is_system_generated=0, read_only=0 WHERE dt='{DOCTYPE}'")
    frappe.db.commit()
    
    frappe.clear_cache()
    print("--- 🏁 Done. Reload Browser. ---")

