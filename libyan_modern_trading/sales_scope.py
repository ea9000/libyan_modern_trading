# LMT sales-document read scope (ticket LMT-HDT-2026-09-27-00012)
# Mirrors the Permission Query Server Scripts lmt_scope_*_v1 for single-document reads.
# System Manager / lmt_so_read_all -> allow; Sales User -> owner must be self or a subordinate;
# everyone else -> untouched (return None = let Frappe decide).
import frappe

SCOPED_PTYPES = ("read", "print", "email", "export", "report", "share")


def _subordinates(user):
    return frappe.get_all("User", filters={"lmt_supervisor_user": user, "enabled": 1}, pluck="name")


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return None
    if ptype and ptype not in SCOPED_PTYPES:
        return None
    roles = set(frappe.get_roles(user))
    if "System Manager" in roles or "lmt_so_read_all" in roles:
        return None
    if "Sales User" not in roles:
        return None
    allowed = [user] + _subordinates(user)
    owner = getattr(doc, "owner", None) or ""
    if owner and owner in allowed:
        return None
    customer = getattr(doc, "customer", None) or ""
    if customer:
        am = frappe.db.get_value("Customer", customer, "account_manager") or ""
        if am and am in allowed:
            return None
    return False
