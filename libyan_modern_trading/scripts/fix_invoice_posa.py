import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🚑 Starting Repair for Sales Invoice (POSA Delivery Charges) ---")

    # STEP 1: FORCE DELETE THE BROKEN FIELD
    # The error explicitly named 'posa_delivery_charges', so we target it directly.
    
    # A. Delete if it is a Custom Field
    bad_fields = frappe.get_all("Custom Field", 
        filters={"fieldname": "posa_delivery_charges", "dt": "Sales Invoice"}, 
        fields=["name"]
    )
    for field in bad_fields:
        print(f"   🗑️  Deleting Broken Custom Field: posa_delivery_charges ({field.name})...")
        frappe.db.delete("Custom Field", field.name)

    # B. Delete if it is a Property Setter (locked standard field)
    bad_props = frappe.get_all("Property Setter", 
        filters={"field_name": "posa_delivery_charges", "doc_type": "Sales Invoice"},
        fields=["name"]
    )
    for prop in bad_props:
        print(f"   🗑️  Deleting Property Setter: posa_delivery_charges ({prop.name})...")
        frappe.db.delete("Property Setter", prop.name)
        
    frappe.db.commit()
    print("   ✅ Cleaned up 'posa_delivery_charges'.")

    # STEP 2: APPLY GENERALIZED FIELDS (Daisy Chain Method)
    print("--- 🔗 Applying Generalized Fields to Sales Invoice ---")
    
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
                    "insert_after": last_field # Daisy chain
                })
                last_field = fname 
        
        return fields

    new_fields_list = get_ordered_fields()
    all_fieldnames = [f["fieldname"] for f in new_fields_list]

    try:
        # Create fields only for Sales Invoice
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
        print("   ✅ Success! Sales Invoice is now fixed and updated.")
        
    except Exception as e:
        print(f"   ❌ Still failing: {str(e)}")
        print("      (Try searching 'posa_delivery_charges' in your database manually if this fails)")

    frappe.clear_cache()

