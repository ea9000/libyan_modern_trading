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


def _is_allowed_for_route(route: str) -> bool:
    user = frappe.session.user
    if user == "Guest":
        return False

    roles = set(frappe.get_roles(user))

    # normalize route
    route = (route or "").strip()
    if not route.startswith("/"):
        route = "/" + route
    route = route.rstrip("/") or "/"

    items = frappe.get_all(
        "LMT Mobile Menu Item",
        filters={"is_active": 1, "route": route},
        fields=["name"],
        limit_page_length=1,
    )

    # secure-by-default: route must exist in menu table
    if not items:
        return False

    it_name = items[0]["name"]

    role_rows = set(frappe.get_all("LMT Menu Role", filters={"parent": it_name}, pluck="role"))
    user_rows = set(frappe.get_all("LMT Menu User", filters={"parent": it_name}, pluck="user"))

    # public item (no roles/users specified)
    if not role_rows and not user_rows:
        return True

    if user in user_rows:
        return True

    if role_rows & roles:
        return True

    return False


@frappe.whitelist()
def is_route_allowed(route: str) -> bool:
    return _is_allowed_for_route(route)
