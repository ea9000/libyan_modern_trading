// LMT impersonation banner v1 — shown on every web page while a supervisor browses as an agent
(function () {
  function show() {
    if (!window.frappe || !frappe.call) return;
    if (document.getElementById('lmt-imp-banner')) return;
    frappe.call({
      method: 'libyan_modern_trading.lmt_impersonate.status',
      callback: function (r) {
        var m = (r && r.message) || {};
        if (!m.active) return;
        var exp = (m.expires || '').slice(11, 16);
        var div = document.createElement('div');
        div.id = 'lmt-imp-banner';
        div.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#b91c1c;color:#fff;font-family:Cairo,sans-serif;font-size:14px;padding:6px 10px;text-align:center;direction:rtl;box-shadow:0 2px 6px rgba(0,0,0,.3)';
        div.innerHTML = '👤 أنت تتصفح كـ <b>' + (m.user || '') + '</b> · ' +
          (m.can_write ? '✏️ الكتابة مسموحة (طلب/مرتجع/تحصيل)' : '🔒 للقراءة فقط') +
          ' · ينتهي ' + exp + ' &nbsp; <button id="lmt-imp-end" style="background:#fde047;color:#000;border:0;border-radius:999px;padding:2px 14px;font-family:inherit;font-weight:700;cursor:pointer">إنهاء الجلسة</button>';
        document.body.appendChild(div);
        document.body.style.paddingTop = div.offsetHeight + 'px';
        document.getElementById('lmt-imp-end').onclick = function () {
          frappe.call({
            method: 'libyan_modern_trading.lmt_impersonate.end',
            callback: function () { window.location.href = '/login'; }
          });
        };
      },
      error: function () {}
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show); else show();
})();
