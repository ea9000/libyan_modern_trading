import frappe

def _require_system_manager():
    # Only System Manager can use this admin page API
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Not permitted", frappe.PermissionError)

@frappe.whitelist()
def list_menu_items():
    _require_system_manager()
    return frappe.get_all(
        "LMT Mobile Menu Item",
        fields=["name", "title_ar", "title_en", "route", "sort_order", "is_active"],
        order_by="sort_order asc, modified desc",
        limit_page_length=500
    )

@frappe.whitelist()
def get_menu_item(name: str):
    _require_system_manager()
    doc = frappe.get_doc("LMT Mobile Menu Item", name)
    return doc.as_dict()

@frappe.whitelist()
def save_menu_item(doc: dict):
    _require_system_manager()

    if isinstance(doc, str):
        # sometimes frappe sends json string
        import json
        doc = json.loads(doc)

    name = doc.get("name")
    if name and frappe.db.exists("LMT Mobile Menu Item", name):
        d = frappe.get_doc("LMT Mobile Menu Item", name)
    else:
        d = frappe.new_doc("LMT Mobile Menu Item")

    # simple fields
    for f in [
        "title_ar","title_en","route",
        "sort_order","is_active","open_in_new_tab",
        "show_on_home_grid","show_on_bottom_nav",
        "icon_type","emoji","fa_class","image_url",
    ]:
        if f in doc:
            d.set(f, doc.get(f))

    # child tables: replace بالكامل
    d.set("allowed_roles", [])
    for r in (doc.get("allowed_roles") or []):
        role = (r.get("role") if isinstance(r, dict) else None)
        if role:
            d.append("allowed_roles", {"role": role})

    d.set("allowed_users", [])
    for u in (doc.get("allowed_users") or []):
        user = (u.get("user") if isinstance(u, dict) else None)
        if user:
            d.append("allowed_users", {"user": user})

    d.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": d.name}

@frappe.whitelist()
def delete_menu_item(name: str):
    _require_system_manager()
    frappe.delete_doc("LMT Mobile Menu Item", name, ignore_permissions=True, force=1)
    frappe.db.commit()
    return {"ok": True}

@frappe.whitelist()
def list_roles():
    _require_system_manager()
    rows = frappe.get_all("Role", fields=["name"], order_by="name asc")
    return [r["name"] for r in rows]

@frappe.whitelist()
def list_users():
    _require_system_manager()
    rows = frappe.get_all(
        "User",
        filters={"enabled": 1},
        fields=["name"],
        order_by="name asc",
        limit_page_length=2000
    )
    return [r["name"] for r in rows]
