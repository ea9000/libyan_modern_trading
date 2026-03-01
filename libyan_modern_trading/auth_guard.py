import frappe

ROLE_PROFILE = "LMT Standard (from Osama)"
LANDING = "/mobile-home"

# Allow what's needed for mobile + password change + app selector + logout
ALLOWED_PREFIXES = (
    "/mobile-home",
    "/assets",
    "/files",
    "/private/files",
    "/api",
    "/update-password",
    "/login",
    "/apps",             # ✅ app selector page
    "/?cmd=web_logout",  # ✅ logout (common)
    "/?cmd=logout",      # ✅ logout (alt)
    "/logout",           # ✅ logout (alt)
)

def _is_target(user: str) -> bool:
    if not user or user in ("Guest", "Administrator"):
        return False
    return frappe.db.get_value("User", user, "role_profile_name") == ROLE_PROFILE

def set_home_for_lmt_standard():
    """After login, force landing page."""
    if _is_target(frappe.session.user):
        frappe.local.response["home_page"] = LANDING

def guard_lmt_standard_routes():
    """Mobile-only access: redirect apps selector to mobile; block Desk; allow needed routes."""
    if not _is_target(frappe.session.user):
        return

    req = getattr(frappe, "request", None)
    path = (req and getattr(req, "path", None)) or "/"

    # ✅ If user lands on app selector, send to mobile landing
    if path == "/apps" or path.startswith("/apps/"):
        return _redirect(LANDING)

    # ✅ HARD BLOCK Desk (no redirect)
    # IMPORTANT: do NOT block "/" because it may route to /apps in some setups
    if path == "/app" or path.startswith("/app/"):
        frappe.throw(
            "Desk access is disabled for your user.",
            frappe.PermissionError
        )

    # Allow required routes
    if any(path.startswith(p) for p in ALLOWED_PREFIXES):
        return

    # Everything else -> mobile landing
    return _redirect(LANDING)

def _redirect(location: str):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = location
