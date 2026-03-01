(function () {
  function go() {
    try {
      const hash = (window.location.hash || "").toLowerCase();
      const isLoginHash = hash === "#login" || hash.startsWith("#login?");
      const isGuest =
        (window.frappe && frappe.session && frappe.session.user === "Guest") ||
        (window.CURRENT_USER === "Guest");

      if (isLoginHash && isGuest) {
        window.location.replace("/lmt-login");
      }
    } catch (e) {}
  }

  // run now + after Frappe router changes hash
  window.addEventListener("hashchange", go);
  document.addEventListener("DOMContentLoaded", go);
  go();
})();
