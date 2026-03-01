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

