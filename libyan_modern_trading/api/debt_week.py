import frappe
from frappe.utils import getdate, add_days, nowdate

# ONLY this role bypasses week lock
BYPASS_ROLES = {"LMT Accountant Bypass"}

DAY_TO_INT = {
    "Saturday": 0,
    "Sunday": 1,
    "Monday": 2,
    "Tuesday": 3,
    "Wednesday": 4,
    "Thursday": 5,
    "Friday": 6,
}

def _today_dow():
    # Python weekday via frappe date (Mon0..Sun6) -> Sat0..Fri6
    return (getdate(nowdate()).weekday() + 2) % 7

def _current_window(start_dow, end_dow):
    today = getdate(nowdate())
    td = _today_dow()

    delta_to_start = (td - start_dow) % 7
    start_date = add_days(today, -delta_to_start)

    if end_dow >= start_dow:
        length = end_dow - start_dow
    else:
        length = (7 - start_dow) + end_dow

    end_date = add_days(start_date, length)
    return start_date, end_date

@frappe.whitelist()
def week_allowed():
    user = frappe.session.user

    # Hard bypass
    if user in ("Administrator", "Guest"):
        return {"allowed": True, "reason": "bypass-user"}

    roles = set(frappe.get_roles(user) or [])
    if roles.intersection(BYPASS_ROLES):
        return {"allowed": True, "reason": "bypass-role"}

    start = frappe.db.get_value("User", user, "lmt_week_start_day")
    end = frappe.db.get_value("User", user, "lmt_week_end_day")

    if not start or not end:
        return {"allowed": False, "reason": "missing-user-week-settings"}

    s = DAY_TO_INT.get(start)
    e = DAY_TO_INT.get(end)
    if s is None or e is None:
        return {"allowed": False, "reason": "invalid-week-settings"}

    ws, we = _current_window(s, e)
    today = getdate(nowdate())

    allowed = (ws <= today <= we)
    return {
        "allowed": allowed,
        "reason": "ok" if allowed else "outside-window",
        "today": str(today),
        "window_start": str(ws),
        "window_end": str(we),
        "start_day": start,
        "end_day": end,
    }
