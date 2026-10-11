# LMT supervisor impersonation — v1
# site_config: lmt_impersonate_enabled (1/0), lmt_impersonate_minutes (default 60),
#              lmt_impersonate_allow (optional list, e.g. ["Sales Order:insert","Sales Order:submit"])
import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, get_datetime, nowdate, cint, flt

ROLE_TEAM = "lmt-impersonate-team"
ROLE_ALL = "lmt-impersonate-all"
ROLE_WRITE = "lmt-impersonate-write"
BLOCKED_ROLES = {"System Manager", "Accounts Manager", ROLE_TEAM, ROLE_ALL, ROLE_WRITE}

COVER_DT = "LMT Impersonation Cover"
LOG_DT = "LMT Impersonation Log"

# doctypes the framework writes on its own while browsing — never block these
SYSTEM_ALLOW = {
    "Activity Log", "Error Log", "Access Log", "Route History", "Version", "Comment",
    "Notification Log", "Email Queue", "Communication", "Prepared Report", "Deleted Document",
    "Scheduled Job Log", "File", "ToDo", "Energy Point Log", "View Log", "Workflow Action", LOG_DT,
}

# business writes allowed for lmt-impersonate-write inside an active cover window
DEFAULT_ALLOW = {
    ("Sales Order", "insert"),
    ("Sales Order", "submit"),
    ("Sales Invoice", "insert"),          # draft RTV only (is_return=1) — see _allowed
    ("LMT Debt Collection", "insert"),
}

DENY_READONLY = "جلسة الإشراف للقراءة فقط — لا يمكن الحفظ أو الاعتماد باسم المندوب."
DENY_COVER = "لا توجد فترة تغطية فعّالة لهذا المندوب — الحفظ غير مسموح."
DENY_ACTION = "هذه العملية غير مسموحة أثناء الدخول كمندوب: {0} / {1}"


# ---------------------------------------------------------------- helpers
def _enabled():
    return cint(frappe.conf.get("lmt_impersonate_enabled")) == 1


def _minutes():
    return cint(frappe.conf.get("lmt_impersonate_minutes")) or 60


def _sess():
    try:
        return frappe.session.data
    except Exception:
        return None


def _dt_exists(dt):
    return bool(frappe.db.exists("DocType", dt))


def _is_supervisor(user):
    return bool(frappe.db.exists("User", {"lmt_supervisor_user": user, "enabled": 1}))


def _target_blocked(user):
    if user in ("Administrator", "Guest"):
        return "admin"
    if not frappe.db.get_value("User", user, "enabled"):
        return "disabled"
    if set(frappe.get_roles(user)) & BLOCKED_ROLES:
        return "privileged"
    if _is_supervisor(user):
        return "supervisor"
    return None


def _active_cover(supervisor, agent):
    if not _dt_exists(COVER_DT):
        return None
    today = nowdate()
    rows = frappe.get_all(
        COVER_DT,
        filters={
            "supervisor": supervisor,
            "agent": agent,
            "status": "Active",
            "from_date": ["<=", today],
            "to_date": [">=", today],
        },
        pluck="name",
        limit=1,
    )
    return rows[0] if rows else None


def _allow_set():
    allow = set(DEFAULT_ALLOW)
    extra = frappe.conf.get("lmt_impersonate_allow")
    if isinstance(extra, (list, tuple)):
        allow = set()
        for s in extra:
            if ":" in str(s):
                d, a = str(s).split(":", 1)
                allow.add((d.strip(), a.strip()))
    return allow


def _allowed(doc, action):
    if (doc.doctype, action) not in _allow_set():
        return False
    if doc.doctype == "Sales Invoice" and not cint(doc.get("is_return")):
        return False
    return True


def _action(doc, method):
    if method == "validate":
        if doc.is_new():
            return "insert"
        act = getattr(doc, "_action", None) or ""
        if act in ("submit", "cancel", "update_after_submit"):
            return act
        return "save"
    return {
        "before_insert": "insert",
        "before_submit": "submit",
        "before_cancel": "cancel",
        "on_trash": "delete",
        "before_update_after_submit": "update_after_submit",
    }.get(method)


def _write_log(caller, user, reason, cover, can_write, expires):
    if not _dt_exists(LOG_DT):
        return None
    try:
        ip = getattr(getattr(frappe.local, "request_ip", None), "__str__", lambda: "")()
    except Exception:
        ip = ""
    d = frappe.get_doc({
        "doctype": LOG_DT,
        "supervisor": caller,
        "agent": user,
        "reason": reason,
        "cover": cover,
        "can_write": can_write,
        "started": now_datetime(),
        "expires": expires,
        "ip": ip,
        "status": "Active",
    })
    d.insert(ignore_permissions=True)
    return d.name


def _close_log(name):
    if not name or not _dt_exists(LOG_DT):
        return
    try:
        frappe.db.set_value(LOG_DT, name, {"ended": now_datetime(), "status": "Ended"}, update_modified=False)
    except Exception:
        pass


def _log_doc(name, doc):
    if not name or not _dt_exists(LOG_DT):
        return
    try:
        log = frappe.get_doc(LOG_DT, name)
        log.append("docs", {
            "ref_doctype": doc.doctype,
            "ref_name": doc.name,
            "amount": flt(doc.get("grand_total") or doc.get("amount") or 0),
        })
        log.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "lmt_impersonate log_doc")


def _activity(caller, user, reason):
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "user": user,
            "status": "Success",
            "operation": "Impersonate",
            "subject": "{0} impersonated {1}: {2}".format(caller, user, reason),
        }).insert(ignore_permissions=True)
    except Exception:
        pass


# ---------------------------------------------------------------- API
@frappe.whitelist()
def candidates():
    """Users the caller may impersonate (for the picker)."""
    if not _enabled():
        return {"enabled": 0, "users": []}
    caller = frappe.session.user
    roles = set(frappe.get_roles(caller))
    if caller == "Administrator":
        roles.add(ROLE_ALL)
    if not (roles & {ROLE_TEAM, ROLE_ALL}):
        return {"enabled": 1, "users": [], "scope": "none"}
    filters = {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}
    scope = "all"
    if ROLE_ALL not in roles:
        filters["lmt_supervisor_user"] = caller
        scope = "team"
    rows = frappe.get_all("User", filters=filters, fields=["name", "full_name"], order_by="full_name")
    out = []
    for r in rows:
        if r.name == caller or _target_blocked(r.name):
            continue
        cover = _active_cover(caller, r.name) if ROLE_WRITE in roles else None
        out.append({"user": r.name, "full_name": r.full_name, "cover": cover})
    return {"enabled": 1, "scope": scope, "can_write_role": int(ROLE_WRITE in roles), "users": out}


@frappe.whitelist()
def login_as(user, reason=None):
    if not _enabled():
        frappe.throw(_("Impersonation disabled"), frappe.PermissionError)
    caller = frappe.session.user
    if caller == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    sess = _sess()
    if sess and sess.get("impersonated_by"):
        frappe.throw("أنت بالفعل داخل جلسة إشراف — أنهِ الجلسة أولاً")
    reason = (reason or "").strip()
    if len(reason) < 3:
        frappe.throw("السبب مطلوب")
    user = (user or "").strip()
    if not user or not frappe.db.exists("User", user):
        frappe.throw(_("User not found"))
    if user == caller:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    roles = set(frappe.get_roles(caller))
    if caller == "Administrator":
        roles.add(ROLE_ALL)
    if not (roles & {ROLE_TEAM, ROLE_ALL}):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    why = _target_blocked(user)
    if why:
        frappe.throw("لا يمكن الدخول كهذا المستخدم ({0})".format(why), frappe.PermissionError)
    if ROLE_ALL not in roles and frappe.db.get_value("User", user, "lmt_supervisor_user") != caller:
        frappe.throw("هذا المندوب ليس ضمن فريقك", frappe.PermissionError)

    cover = _active_cover(caller, user) if ROLE_WRITE in roles else None
    can_write = 1 if cover else 0
    expires = add_to_date(now_datetime(), minutes=_minutes())

    log = _write_log(caller, user, reason, cover, can_write, expires)
    _activity(caller, user, reason)

    frappe.local.login_manager.login_as(user)
    data = frappe.session.data
    data.impersonated_by = caller
    data.impersonation_expires = str(expires)
    data.impersonation_can_write = can_write
    data.impersonation_cover = cover
    data.impersonation_log = log
    return {"ok": 1, "user": user, "can_write": can_write, "expires": str(expires), "cover": cover}


@frappe.whitelist()
def status():
    sess = _sess() or {}
    imp = sess.get("impersonated_by")
    if not imp:
        return {"active": 0}
    return {
        "active": 1,
        "impersonated_by": imp,
        "user": frappe.session.user,
        "can_write": cint(sess.get("impersonation_can_write")),
        "expires": sess.get("impersonation_expires"),
        "cover": sess.get("impersonation_cover"),
    }


@frappe.whitelist()
def end():
    sess = _sess()
    if sess and sess.get("impersonated_by"):
        _close_log(sess.get("impersonation_log"))
    frappe.local.login_manager.logout()
    return {"ok": 1}


# ---------------------------------------------------------------- hooks
def guard_request():
    """before_request: expire impersonated sessions. Never raises."""
    try:
        if not _enabled():
            return
        sess = _sess()
        if not sess or not sess.get("impersonated_by"):
            return
        exp = sess.get("impersonation_expires")
        if exp and get_datetime(exp) < now_datetime():
            _close_log(sess.get("impersonation_log"))
            frappe.local.login_manager.logout()
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/login?impersonation=expired"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "lmt_impersonate guard_request")
        except Exception:
            pass


def guard_doc(doc, method=None):
    """doc_events '*': deny writes in impersonated sessions unless allowed; stamp docs."""
    try:
        if not _enabled():
            return
        sess = _sess()
        imp = sess.get("impersonated_by") if sess else None
    except Exception:
        return
    if not imp:
        return
    if doc.doctype in SYSTEM_ALLOW or getattr(doc.meta, "istable", 0):
        return
    action = _action(doc, method)
    if action is None:
        return
    if not cint(sess.get("impersonation_can_write")):
        frappe.throw(DENY_READONLY, frappe.PermissionError)
    if not _active_cover(imp, frappe.session.user):
        frappe.throw(DENY_COVER, frappe.PermissionError)
    if not _allowed(doc, action):
        frappe.throw(DENY_ACTION.format(doc.doctype, action), frappe.PermissionError)
    if action == "insert" and doc.meta.has_field("custom_impersonated_by"):
        doc.custom_impersonated_by = imp


def after_insert_doc(doc, method=None):
    try:
        sess = _sess()
        imp = sess.get("impersonated_by") if sess else None
        if not imp or doc.doctype in SYSTEM_ALLOW or getattr(doc.meta, "istable", 0):
            return
        _log_doc(sess.get("impersonation_log"), doc)
    except Exception:
        pass
