# -*- coding: utf-8 -*-

app_name = "libyan_modern_trading"
app_title = "Libyan Modern Trading"
app_publisher = "LMT"
app_description = "Libyan Modern Trading customizations"
app_email = "admin@example.com"
app_license = "MIT"

# OPTIONAL: app selector styling (some versions use this, some ignore it)
app_icon = "octicon octicon-briefcase"
app_color = "blue"

# OPTIONAL: Desk landing page (NOT website home)
# app_home = "lmt_home"

# ✅ Make it appear on Apps page + in User Settings -> Default App
# Choose a route that exists:
# - "/app" opens Desk
# - "/app/home" opens the main workspace/home
# - "/app/lmt-home" if you have a workspace/page with that route

add_to_apps_screen = [
    {
        "name": "libyan_modern_trading",
        "title": "الشركة الليبية الحديثة",
        "route": "/mobile-home",
        "logo": "/assets/libyan_modern_trading/icons/4-2-retail-free-png-image.png",
    }
]

# ✅ Combine both before_request hooks in ONE list (no overwriting)
before_request = [
    "libyan_modern_trading.website_guard.guard_website_routes",
    "libyan_modern_trading.auth_guard.guard_lmt_standard_routes",
]

on_session_creation = [
    "libyan_modern_trading.auth_guard.set_home_for_lmt_standard",
]

app_include_js = [
    "/assets/libyan_modern_trading/js/force_mobile_home.js",
    "/assets/libyan_modern_trading/js/lmt_hash_login_redirect.js",

]
app_include_css = [
    "/assets/libyan_modern_trading/css/pwa.css",
]

app_include_js = [
    "/assets/lmt_custom/js/disable_sw.js"
]

# ✅ Inject dynamic LMT colors into every web page
# CORRECT
update_website_context = ["libyan_modern_trading.utils.website_utils.get_website_context"]

# =================================================================
# FIXTURES — for disaster recovery & git backup
# =================================================================

def _load_fixtures_list():
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "fixtures_list.json")
    if not os.path.exists(path):
        return [], []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scripts = list(set(
        data.get("scripts_api", []) +
        data.get("scripts_doctype_event", []) +
        data.get("scripts_indirect", []) +
        data.get("scripts_scheduler", []) +
        data.get("scripts_permission", [])
    ))
    return scripts, data.get("webpages", [])

_scripts, _webpages = _load_fixtures_list()

fixtures = [
    {"dt": "Server Script", "filters": [["name", "in", _scripts]]} if _scripts else "Server Script",
    {"dt": "Web Page", "filters": [["name", "in", _webpages]]} if _webpages else "Web Page",
    "Client Script",
    {"dt": "DocType", "filters": [["custom", "=", 1]]},
    {"dt": "DocType", "filters": [["module", "in", ["Libyan Modern Trading", "LMT Helpdesk"]], ["custom", "=", 0]]},
    "Custom Field",
    "Property Setter",
    {"dt": "Print Format", "filters": [["standard", "=", "No"]]},
    "Notification",
    "LMT Mobile Menu Item",
    "LMT Report Menu Item",
]

# Clean up namespace
del _scripts, _webpages, _load_fixtures_list

