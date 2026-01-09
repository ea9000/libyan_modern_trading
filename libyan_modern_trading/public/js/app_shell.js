/**
 * ملف LMT App Shell JS (القائمة الجانبية + التنقل)
 * يدعم كلا نظامي CSS:
 * - المعتمد على الإخفاء (فئة "hidden")
 * - المعتمد على الفتح (فئة "open" للتمرير الجانبي)
 */
(function () {
  "use strict";

  function el(id){ return document.getElementById(id); }

  function addClass(x, c){ if (x) x.classList.add(c); }
  function remClass(x, c){ if (x) x.classList.remove(c); }
  function hasClass(x, c){ return x ? x.classList.contains(c) : false; }

  function openDrawer(){
    var d = el("drawer");
    var o = el("drawerOverlay");

    // التأكد من أنها ليست مخفية
    remClass(d, "hidden");
    remClass(o, "hidden");

    // لنظام التمرير الجانبي في CSS
    addClass(d, "open");
    addClass(o, "open");
  }

  function closeDrawer(){
    var d = el("drawer");
    var o = el("drawerOverlay");

    // إزالة فئة التمرير الجانبي
    remClass(d, "open");
    remClass(o, "open");

    // الإخفاء الفعلي (يعمل مع كلا النظامين)
    addClass(d, "hidden");
    addClass(o, "hidden");
  }

  function toggleDrawer(){
    var d = el("drawer");
    if (!d) return;

    // إذا كانت مخفية أو ليست مفتوحة -> قم بفتحها
    if (hasClass(d, "hidden") || !hasClass(d, "open")) openDrawer();
    else closeDrawer();
  }

  function setTitle(){
    var t = el("topbarTitle");
    if (!t) return;

    if (window.PAGE_TITLE) { t.textContent = window.PAGE_TITLE; return; }

    // العودة إلى العنوان الافتراضي عبر ACTIVE_KEY
    var key = window.ACTIVE_KEY || "";
    // تحديث: إضافة split_customer إلى الخريطة لضمان العنوان الصحيح
    var map = { 
        orders: "navOrders", 
        customers: "navCustomers", 
        split_customer: "navCustomers", 
        report: "navReport", 
        debt: "navDebt" 
    };
    var nav = map[key] ? el(map[key]) : null;
    if (nav && nav.dataset && nav.dataset.title) t.textContent = nav.dataset.title;
  }

  function bindBottomNav(){
    // تحديث: تغيير المسار لـ navCustomers إلى /split_customer
    var routes = {
      navOrders: "/split_order",
      navCustomers: "/split_customer",
      navReport: "/mobile-report",
      navDebt: "/mobile-debt"
    };

    Object.keys(routes).forEach(function(id){
      var n = el(id);
      if (!n) return;
      n.addEventListener("click", function(){ window.location.href = routes[id]; });
    });
  }

  function bind(){
    var btnMenu = el("btnMenu");
    var overlay = el("drawerOverlay");
    var btnRefresh = el("btnRefresh");

    if (btnMenu) btnMenu.addEventListener("click", toggleDrawer);
    if (overlay) overlay.addEventListener("click", closeDrawer);
    if (btnRefresh) btnRefresh.addEventListener("click", function(){ location.reload(); });

    document.addEventListener("keydown", function(e){
      if (e.key === "Escape") closeDrawer();
    });

    setTitle();
    bindBottomNav();

    // التأكد من إغلاقها مبدئياً
    closeDrawer();

    console.log("تم تحميل app_shell.js: مفعل القائمة الجانبية نشط");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
