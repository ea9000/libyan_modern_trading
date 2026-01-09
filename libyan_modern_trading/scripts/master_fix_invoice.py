import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🧹 Starting Master Cleanup for Sales Invoice ---")
    
    # STEP 1: SCAN AND DELETE ALL BROKEN LINK FIELDS
    # instead of guessing names, we check the database for validity.
    
    print("1. Scanning for broken links...")
    custom_link_fields = frappe.get_all("Custom Field", 
        filters={"dt": "Sales Invoice", "fieldtype": "Link"}, 
        fields=["name", "fieldname", "options", "label"]
    )

    deleted_count = 0
    
    for field in custom_link_fields:
        target_doctype = field.options
        
        # If the target DocType (e.g. "Loan Repayment") does not exist...
        if target_doctype and not frappe.db.exists("DocType", target_doctype):
            print(f"   ❌ Found Zombie Field: '{field.label}' ({field.fieldname}) linking to missing '{target_doctype}'")
            print(f"      🗑️  Deleting {field.name}...")
            frappe.db.delete("Custom Field", field.name)
            deleted_count += 1

    # Also check Property Setters (standard fields modified to link to bad docs)
    props = frappe.get_all("Property Setter", 
        filters={"doc_type": "Sales Invoice", "property": "options"}, 
        fields=["name", "value", "field_name"]
    )
    for p in props:
        if p.value and not frappe.db.exists("DocType", p.value) and p.value != "User": # Ignore basic types
            print(f"   ❌ Found Broken Property Setter on '{p.field_name}' linking to '{p.value}'")
            frappe.db.delete("Property Setter", p.name)
            deleted_count += 1
            
    frappe.db.commit()
    
    if deleted_count == 0:
        print("   ✅ No broken links found.")
    else:
        print(f"   ✅ Deleted {deleted_count} broken fields/properties.")

    # STEP 2: RE-APPLY GENERALIZED FIELDS
    print("--- 🔗 Re-applying Generalized Fields ---")
    
    def get_ordered_fields():
        fields = []
        last_field = "connections_tab"
        
        # 1. Tab Break
        fields.append({
            "fieldname": "custom_tab_generalized_code",
            "label": "Generalized Code",
            "fieldtype": "Tab Break",
            "insert_after": last_field
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

        # 3. The 20 Fields (5 of each)
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

    new_fields_list = get_ordered_fields()
    all_fieldnames = [f["fieldname"] for f in new_fields_list]

    try:
        create_custom_fields({"Sales Invoice": new_fields_list})
        
        # Fix Permissions
        placeholders = ', '.join(['%s'] * len(all_fieldnames))
        sql = f"""
            UPDATE `tabCustom Field`
            SET is_system_generated = 0, read_only = 0
            WHERE dt = 'Sales Invoice' AND fieldname IN ({placeholders})
        """
        frappe.db.sql(sql, tuple(all_fieldnames))
        
        frappe.db.commit()
        print("   ✅ Success! Sales Invoice is fully repaired and updated.")
        
    except Exception as e:
        print(f"   ❌ Final Error: {str(e)}")

    frappe.clear_cache()
