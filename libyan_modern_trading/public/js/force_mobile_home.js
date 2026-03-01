(function () {
  function go() {
    try {
      if (!window.frappe || !frappe.boot || !frappe.boot.user) return;

      const rp = frappe.boot.user.role_profile_name;
      if (rp === "LMT Standard (from Osama)") {
        if (!location.pathname.startsWith("/mobile-home")) {
          location.replace("/mobile-home");
        }
      }
    } catch (e) {
      // no-op
    }
  }

  // run now and after a short delay (covers boot timing)
  go();
  setTimeout(go, 300);
  setTimeout(go, 1200);
})();
