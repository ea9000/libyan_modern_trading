import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🚀 Starting: Adding 5 'Generalized Fields' of each type ---")

    # ---------------------------------------------------------
    # CONFIGURATION: Target DocTypes
    # ---------------------------------------------------------
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
    # GENERATE FIELD DEFINITIONS (5 of each)
    # ---------------------------------------------------------
    
    common_fields = [
        {
            "fieldname": "custom_tab_generalized_code",
            "label": "Generalized Code",
            "fieldtype": "Tab Break",
            "insert_after": "connections_tab"
        },
        {
            "fieldname": "custom_sec_generalized_code",
            "label": "",
            "fieldtype": "Section Break",
        }
    ]

    # Helper to generate 5 fields per type
    def generate_fields(prefix, label_prefix, fieldtype):
        generated = []
        # CHANGED: range(1, 6) creates fields 1 through 5
        for i in range(1, 6):
            generated.append({
                "fieldname": f"custom_{prefix}_{i}",
                "label": f"{label_prefix} {i}",
                "fieldtype": fieldtype,
                "allow_on_submit": 1,
                "default": 0 if fieldtype in ["Check", "Int", "Float"] else None
            })
        return generated

    # Create the 4 groups of 5
    fields_log = generate_fields("log", "LOG", "Check")
    fields_txt = generate_fields("txt", "TXT", "Data")
    fields_dec = generate_fields("dec", "DEC", "Float")
    fields_int = generate_fields("int", "INT", "Int")

    # Combine all fields (Tab + Section + 20 Fields)
    all_new_fields = common_fields + fields_log + fields_txt + fields_dec + fields_int

    # ---------------------------------------------------------
    # EXECUTION
    # ---------------------------------------------------------
    
    print(f"📋 Target DocTypes: {len(target_doctypes)}")
    print(f"fields to add per DocType: {len(all_new_fields)}")

    for dt in target_doctypes:
        print(f"   👉 Processing: {dt}...")
        
        fields_map = { dt: all_new_fields }

        try:
            create_custom_fields(fields_map)
            
            # Force 'Standard' behavior (Editable & Not System Generated)
            new_fieldnames = [f["fieldname"] for f in all_new_fields]
            placeholders = ', '.join(['%s'] * len(new_fieldnames))
            
            sql = f"""
                UPDATE `tabCustom Field`
                SET is_system_generated = 0, read_only = 0
                WHERE dt = %s AND fieldname IN ({placeholders})
            """
            params = tuple([dt] + new_fieldnames)
            frappe.db.sql(sql, params)
            
        except Exception as e:
            print(f"      ❌ Error on {dt}: {str(e)}")

    frappe.db.commit()
    print("--- ✅ DONE. Clearing Cache... ---")
    frappe.clear_cache()

