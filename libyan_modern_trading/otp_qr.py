# LMT-OTP-QR v1 — same-phone 2FA enrollment helper (ticket LMT-HDT-2026-10-22-00004)
# Guest method: k = key from the Frappe OTP email (/qrcode?k=...). Returns what frappe/www/qrcode.py renders,
# plus the raw otpauth:// uri and the base32 secret so the phone can open the authenticator app directly
# or type the key manually. Same exposure as the stock page (the QR already encodes the secret). Key lives
# in cache for System Settings.lifespan_qrcode_image seconds only.
import re
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def lmt_otp_uri(k=None):
    k = (k or "").strip()
    if not k or len(k) > 64 or not re.match(r"^[A-Za-z0-9_-]+$", k):
        frappe.throw(_("Invalid key"), frappe.PermissionError)
    totp_uri = frappe.cache.get_value(k + "_uri") or frappe.cache.get_value(k)
    user = frappe.cache.get_value(k + "_user")
    if not totp_uri or not user:
        return {"ok": 0, "reason": "expired"}
    if isinstance(totp_uri, bytes):
        totp_uri = totp_uri.decode("utf-8")
    if isinstance(user, bytes):
        user = user.decode("utf-8")
    secret = ""
    try:
        secret = parse_qs(urlparse(totp_uri).query).get("secret", [""])[0]
    except Exception:
        secret = ""
    svg = ""
    try:
        from frappe.twofactor import get_qr_svg_code

        svg = get_qr_svg_code(totp_uri)
        if isinstance(svg, bytes):
            svg = svg.decode("utf-8")
    except Exception:
        svg = ""
    full_name = frappe.db.get_value("User", user, "full_name") or user
    return {"ok": 1, "user": user, "full_name": full_name, "uri": totp_uri, "secret": secret, "svg": svg}
