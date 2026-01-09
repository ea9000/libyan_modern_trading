import frappe

@frappe.whitelist()
def list_menu_items():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    items = frappe.get_all(
        "LMT Mobile Menu Item",
        filters={"is_active": 1},
        fields=[
            "name", "title_ar", "title_en", "route",
            "icon_type", "emoji", "fa_class", "image_url",
            "show_on_home_grid", "show_on_bottom_nav",
            "sort_order"
        ],
        order_by="sort_order asc"
    )

    allowed = []

    for it in items:
        ok = False

        # role-based
        role_rows = frappe.get_all(
            "LMT Menu Role",
            filters={"parent": it.name},
            pluck="role"
        )
        if role_rows and set(role_rows) & set(roles):
            ok = True

        # user-based
        user_rows = frappe.get_all(
            "LMT Menu User",
            filters={"parent": it.name},
            pluck="user"
        )
        if user in user_rows:
            ok = True

        if not role_rows and not user_rows:
            ok = True  # public item

        if ok:
            allowed.append(it)

    return allowed
