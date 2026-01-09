import frappe

def _pick_insert_after_tab(dt="Sales Order"):
    meta = frappe.get_meta(dt)
    tab_fields = [f for f in meta.fields if f.fieldtype == "Tab Break"]

    for f in tab_fields:
        if f.fieldname == "connections_tab":
            return "connections_tab"

    for f in tab_fields:
        if (f.label or "").strip().lower() == "connections":
            return f.fieldname

    if tab_fields:
        return tab_fields[-1].fieldname

    return "terms"

def ensure_custom_field(df):
    name = f"{df['dt']}-{df['fieldname']}"
    exists = frappe.db.exists("Custom Field", name)

    if exists:
        doc = frappe.get_doc("Custom Field", name)
        for k, v in df.items():
            if k == "dt":
                continue
            doc.set(k, v)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({"doctype": "Custom Field", **df})
        doc.insert(ignore_permissions=True)

def run():
    frappe.flags.in_patch = True

    dt = "Sales Order"
    insert_after_tab = _pick_insert_after_tab(dt)

    ensure_custom_field(dict(
        dt=dt,
        fieldname="custom_special_fields",
        label="Special Fields",
        fieldtype="Tab Break",
        insert_after=insert_after_tab,
    ))

    ensure_custom_field(dict(
        dt=dt,
        fieldname="custom_special_discount_section",
        label="Discount Settings",
        fieldtype="Section Break",
        insert_after="custom_special_fields",
    ))

    ensure_custom_field(dict(
        dt=dt,
        fieldname="custom_special_discount",
        label="Special Discount",
        fieldtype="Check",
        insert_after="custom_special_discount_section",
    ))

    ensure_custom_field(dict(
        dt=dt,
        fieldname="custom_special_discount_customer_pct",
        label="Special Discount - Customer %",
        fieldtype="Percent",
        depends_on="eval:doc.custom_special_discount==1",
        insert_after="custom_special_discount",
    ))

    ensure_custom_field(dict(
        dt=dt,
        fieldname="custom_special_discount_agent_pct",
        label="Special Discount - Agent %",
        fieldtype="Percent",
        depends_on="eval:doc.custom_special_discount==1",
        insert_after="custom_special_discount_customer_pct",
    ))

    frappe.db.commit()
    print("OK: Sales Order special fields created/updated.")
    print("Inserted tab after:", insert_after_tab)
