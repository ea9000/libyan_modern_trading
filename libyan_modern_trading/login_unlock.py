# LMT login unlock tool - consumer: lmt-helpdesk (admin only)
import frappe
from frappe.utils import cint, get_datetime, now_datetime

KEYS = ("login_failed_count", "login_failed_time", "locked_account_time")


def _require_admin():
    user = frappe.session.user
    if user == "Administrator":
        return
    if "System Manager" not in frappe.get_roles(user):
        frappe.throw("غير مصرح", frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def list_locks():
    _require_admin()
    max_att = cint(frappe.db.get_single_value("System Settings", "allow_consecutive_login_attempts"))
    lock_sec = cint(frappe.db.get_single_value("System Settings", "allow_login_after_fail")) or 60
    counts = frappe.cache.hgetall("login_failed_count") or {}
    times = frappe.cache.hgetall("login_failed_time") or {}
    now = now_datetime()
    rows = []
    for key, cnt in counts.items():
        k = key.decode() if isinstance(key, bytes) else str(key)
        t = times.get(key)
        if t is None:
            t = times.get(k)
        since = ""
        age = None
        if t:
            try:
                dt = get_datetime(t)
                since = str(dt)[:19]
                age = int((now - dt).total_seconds())
            except Exception:
                age = None
        locked = bool(max_att and cint(cnt) >= max_att and age is not None and age < lock_sec)
        kind = "user" if frappe.db.exists("User", k) else "ip"
        rows.append({
            "key": k,
            "kind": kind,
            "count": cint(cnt),
            "since": since,
            "locked": 1 if locked else 0,
            "seconds_left": max(lock_sec - age, 0) if (locked and age is not None) else 0,
        })
    rows.sort(key=lambda r: (-r["locked"], -r["count"], r["key"]))
    return {"ok": 1, "max_attempts": max_att, "lock_seconds": lock_sec, "my_ip": frappe.local.request_ip, "rows": rows}


@frappe.whitelist(methods=["POST"])
def unlock(key=None, unlock_all=0):
    _require_admin()
    done = []
    if cint(unlock_all):
        for k in KEYS:
            frappe.cache.delete_value(k)
        done.append("ALL")
    else:
        key = (key or "").strip()
        if not key:
            frappe.throw("المفتاح مطلوب")
        for k in KEYS:
            try:
                frappe.cache.hdel(k, key)
            except Exception:
                pass
        done.append(key)
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "User",
        "reference_name": frappe.session.user,
        "content": "Login unlock: " + ", ".join(done),
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": 1, "unlocked": done}
