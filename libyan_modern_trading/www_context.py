import frappe
from libyan_modern_trading.api.menu import _is_allowed_for_route

def get_context(context):
    path = (frappe.request.path or "").rstrip("/") or "/"

    protected_prefixes = ("/split-", "/mobile-", "/warehouse", "/menu-admin")

    if path.startswith(protected_prefixes):
        if not _is_allowed_for_route(path):
            frappe.throw("Not permitted", frappe.PermissionError)
