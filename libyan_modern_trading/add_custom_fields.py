import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup():
    # Fields for Agent (User)
    # Fields for Customer Type
    fields = {
        "User": [
            {"fieldname": "lmt_percentage_1", "label": "Pharmacy %", "fieldtype": "Float", "insert_after": "email"},
            {"fieldname": "lmt_percentage_2", "label": "Company %", "fieldtype": "Float", "insert_after": "lmt_percentage_1"},
            {"fieldname": "lmt_booklet_start", "label": "Booklet Start", "fieldtype": "Int", "insert_after": "lmt_percentage_2"},
            {"fieldname": "lmt_booklet_end", "label": "Booklet End", "fieldtype": "Int", "insert_after": "lmt_booklet_start"}
        ],
        "Customer": [
            {"fieldname": "lmt_cust_type", "label": "LMT Type", "fieldtype": "Select", "options": "Pharmacy\nCompany", "insert_after": "customer_group"}
        ]
    }
    create_custom_fields(fields)
    frappe.db.commit()

if __name__ == "__main__":
    setup()
