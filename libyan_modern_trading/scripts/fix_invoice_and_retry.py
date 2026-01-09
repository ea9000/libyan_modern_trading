import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🚑 Starting Repair for Sales Invoice ---")

    # STEP 1: Find and Destroy the "Zombie" Loan Field
    # We look for any field in Sales Invoice that links to 'Loan'
    bad_fields = frappe.get_all("Custom Field", 
        filters={"dt": "Sales Invoice", "options": "Loan"}, 
        fields=["name", "fieldname"]
    )

    if bad_fields:
        for field in bad_fields:
            print(f"   🗑️  Deleting broken field: {field.fieldname} ({field.name})...")
            frappe.db.delete("Custom Field", field.name)
        frappe.db.commit()
        print("   ✅ Broken fields removed.")
    else:
        print("   ℹ️  No custom 'Loan' fields found. Checking standard fields (cannot delete, but will warn)...")
        # Sometimes it's not a custom field, but a leftover property setter
        frappe.db.delete("Property Setter", {"doc_type": "Sales Invoice", "property": "options", "value": "Loan"})
        frappe.db.commit()

    # STEP 2: Retry Adding Generalized Fields to Sales Invoice
    print("--- 🔄 Retrying Generalized Fields for Sales Invoice ---")
    
    # We redefine the fields just for Sales Invoice
    common_fields = [
        {"fieldname": "custom_tab_generalized_code", "label": "Generalized Code", "fieldtype": "Tab Break", "insert_after": "connections_tab"},
        {"fieldname": "custom_sec_generalized_code", "label": "", "fieldtype": "Section Break"}
    ]

    def generate_fields(prefix, label_prefix, fieldtype):
        generated = []
        for i in range(1, 6):
            generated.append({
                "fieldname": f"custom_{prefix}_{i}",
                "label": f"{label_prefix} {i}",
                "fieldtype": fieldtype,
                "allow_on_submit": 1,
                "default": 0 if fieldtype in ["Check", "Int", "Float"] else None
            })
        return generated

    all_new_fields = common_fields + \
                     generate_fields("log", "LOG", "Check") + \
                     generate_fields("txt", "TXT", "Data") + \
                     generate_fields("dec", "DEC", "Float") + \
                     generate_fields("int", "INT", "Int")

    try:
        create_custom_fields({"Sales Invoice": all_new_fields})
        
        # SQL Fix for permissions
        new_fieldnames = [f["fieldname"] for f in all_new_fields]
        placeholders = ', '.join(['%s'] * len(new_fieldnames))
        sql = f"UPDATE `tabCustom Field` SET is_system_generated = 0, read_only = 0 WHERE dt = 'Sales Invoice' AND fieldname IN ({placeholders})"
        params = tuple(new_fieldnames)
        frappe.db.sql(sql, params)
        frappe.db.commit()
        print("   ✅ Success! Sales Invoice is now updated.")
        
    except Exception as e:
        print(f"   ❌ Still failing: {str(e)}")
        print("      (If this persists, go to 'Customize Form' > 'Sales Invoice' manually and delete the row with 'Loan' in Options)")

    frappe.clear_cache()

