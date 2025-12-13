// ================= SETTINGS =================
const FEATURES = {
  orders: true,
  customers: true,
  report: true,
  debt: true
};

const ROUTES = {
  orders: "/mobile-orders",
  customers: "/mobile-customers",
  report: "/mobile-report",
  debt: "/mobile-debt"
};

// ================= HELPERS =================
function setVisible(id, visible) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden", !visible);
}

function setTopbarTitle(title) {
  const el = document.getElementById("topbarTitle");
  if (el) el.textContent = title;
}

function setActiveNav(id) {
  document.querySelectorAll(".nav-item")
    .forEach(n => n.classList.remove("active"));
  const el = document.getElementById(id);
  if (el) el.classList.add("active");
}

// ================= INIT =================
function initHome() {
  setVisible("navOrders", FEATURES.orders);
  setVisible("navCustomers", FEATURES.customers);
  setVisible("navReport", FEATURES.report);
  setVisible("navDebt", FEATURES.debt);

  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const key = item.dataset.key;
      if (!FEATURES[key]) return;

      setActiveNav(item.id);
      setTopbarTitle(item.dataset.title);
      window.location.href = ROUTES[key];
    });
  });

  const refreshBtn = document.getElementById("btnRefresh");
  if (refreshBtn) refreshBtn.onclick = () => location.reload();
}

document.addEventListener("DOMContentLoaded", initHome);
