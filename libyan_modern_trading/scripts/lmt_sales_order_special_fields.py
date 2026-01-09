import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- Starting Custom Field Creation for Sales Order ---")
    
    fields = {
        "Sales Order": [
            # 1. New Tab: Special Fields
            {
                "fieldname": "custom_tab_special_fields",
                "label": "Special Fields",
                "fieldtype": "Tab Break",
                "insert_after": "terms_tab" # Inserts after the last standard tab usually
            },
            # 2. Section Break
            {
                "fieldname": "custom_special_discount_section",
                "label": "Special Discount Details",
                "fieldtype": "Section Break",
                "insert_after": "custom_tab_special_fields"
            },
            # 3. Special Discount (Logical Check)
            {
                "fieldname": "custom_special_discount",
                "label": "Special Discount",
                "fieldtype": "Check",
                "default": 0,
                "insert_after": "custom_special_discount_section"
            },
            # 4. Special Discount – Customer %
            {
                "fieldname": "custom_special_discount_customer_pct",
                "label": "Special Discount – Customer",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount"
            },
            # 5. Special Discount – Agent %
            {
                "fieldname": "custom_special_discount_agent_pct",
                "label": "Special Discount – Agent",
                "fieldtype": "Percent",
                "depends_on": "eval:doc.custom_special_discount==1",
                "insert_after": "custom_special_discount_customer_pct"
            }
        ]
    }

    create_custom_fields(fields)
    frappe.db.commit()
    print("--- Fields Created Successfully ---")
