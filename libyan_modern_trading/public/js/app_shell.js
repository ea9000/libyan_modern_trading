/**
 * LMT App Shell JS (drawer + nav)
 * Supports BOTH CSS schemes:
 *  - hidden-based (class "hidden")
 *  - open-based (class "open" for slide-in)
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

    // make sure they are not hidden
    remClass(d, "hidden");
    remClass(o, "hidden");

    // for slide-in CSS
    addClass(d, "open");
    addClass(o, "open");
  }

  function closeDrawer(){
    var d = el("drawer");
    var o = el("drawerOverlay");

    // remove slide-in class
    remClass(d, "open");
    remClass(o, "open");

    // also hide (works for both systems)
    addClass(d, "hidden");
    addClass(o, "hidden");
  }

  function toggleDrawer(){
    var d = el("drawer");
    if (!d) return;

    // if either hidden OR not open -> open
    if (hasClass(d, "hidden") || !hasClass(d, "open")) openDrawer();
    else closeDrawer();
  }

  function setTitle(){
    var t = el("topbarTitle");
    if (!t) return;

    if (window.PAGE_TITLE) { t.textContent = window.PAGE_TITLE; return; }

    // fallback via ACTIVE_KEY
    var key = window.ACTIVE_KEY || "";
    var map = { orders:"navOrders", customers:"navCustomers", report:"navReport", debt:"navDebt" };
    var nav = map[key] ? el(map[key]) : null;
    if (nav && nav.dataset && nav.dataset.title) t.textContent = nav.dataset.title;
  }

  function bindBottomNav(){
    var routes = {
      navOrders: "/mobile-orders",
      navCustomers: "/mobile-customers",
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

    // ensure closed initially
    closeDrawer();

    console.log("app_shell.js loaded: drawer binder active");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
