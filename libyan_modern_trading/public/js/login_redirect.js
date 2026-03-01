// Runs on Desk login page (/#login)
(function () {
  try {
    const hash = (window.location.hash || "").toLowerCase();
    const isLoginHash = hash === "#login" || hash.startsWith("#login?");
    if (isLoginHash) {
      window.location.replace("/lmt-login");
    }
  } catch (e) {}
})();
