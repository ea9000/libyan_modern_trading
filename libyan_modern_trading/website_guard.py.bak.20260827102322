import frappe
from frappe.exceptions import Redirect

# Paths that must NEVER be blocked (system / assets / api / login etc.)
ALLOW_PREFIXES = (
    "/app", "/api", "/assets", "/files", "/private", "/backups",
    "/_health", "/__debugger__", "/socket.io", "/desk"
)

ALLOW_EXACT = (
    "/", "/login", "/update-password", "/forgot", "/me"
)

def _norm_route(path: str) -> str:
    if not path:
        return "/"
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    # remove trailing slash (except root)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path

def _is_public_path(path: str) -> bool:
    if path in ALLOW_EXACT:
        return True
    return any(path.startswith(p) for p in ALLOW_PREFIXES)

def _get_menu_item_by_route(route: str):
    """
    Match only routes that are registered in LMT Mobile Menu Item.
    This guard only applies to those routes. All other website routes pass through.
    """
    route = _norm_route(route)
    alt = route[1:] if route.startswith("/") else route

    rows = frappe.get_all(
        "LMT Mobile Menu Item",
        filters={"is_active": 1, "route": ["in", [route, alt]]},
        fields=["name", "route"],
        limit_page_length=1
    )
    return rows[0] if rows else None

def guard_website_routes():
    """
    OPTION A (as requested):
      - If the requested path matches a configured LMT Mobile Menu Item route:
          * Guest -> redirect to login
          * Logged-in -> always allow page load
      - Actual DocType permissions are enforced by API calls (frappe.client.* etc.)
        so we do NOT block logged-in users here.

    This prevents confusing "Not permitted / DocType - None" errors on page load.
    """
    try:
        req = getattr(frappe.local, "request", None)
        if not req:
            return

        path = _norm_route(getattr(req, "path", "") or "/")

        # Never block system/desk/api/assets routes
        if _is_public_path(path):
            return

        # Only enforce rules for routes that are in LMT Mobile Menu Item
        item = _get_menu_item_by_route(path)
        if not item:
            return

        user = frappe.session.user or "Guest"

        # Guest tries protected route => redirect to login
        if user == "Guest":
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/login?redirect-to=" + path
            raise Redirect

        # Logged-in users: allow page load.
        # DocType/API permissions will enforce insert/update/read.
        return

    except Redirect:
        raise
    except Exception:
        # Never crash the whole website due to guard logic
        frappe.log_error(title="LMT Website Route Guard Error")
        return
