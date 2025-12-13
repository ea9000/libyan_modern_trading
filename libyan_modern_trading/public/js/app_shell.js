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
  if (el) el.textContent = title || "";
}

function setActiveNavByKey(key) {
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const map = { report: "navReport", customers: "navCustomers", orders: "navOrders", debt: "navDebt" };
  const id = map[key];
  if (id) document.getElementById(id)?.classList.add("active");
}

function openDrawer() {
  document.getElementById("drawer")?.classList.remove("hidden");
  document.getElementById("drawerOverlay")?.classList.remove("hidden");
}
function closeDrawer() {
  document.getElementById("drawer")?.classList.add("hidden");
  document.getElementById("drawerOverlay")?.classList.add("hidden");
}

// ================= INIT =================
function initShell() {
  // show/hide nav by feature
  setVisible("navOrders", FEATURES.orders);
  setVisible("navCustomers", FEATURES.customers);
  setVisible("navReport", FEATURES.report);
  setVisible("navDebt", FEATURES.debt);

  // set title + active
  const key = window.ACTIVE_KEY || "orders";
  const title = window.PAGE_TITLE || (document.getElementById("navOrders")?.dataset?.title ?? "Orders");
  setActiveNavByKey(key);
  setTopbarTitle(title);

  // drawer
  document.getElementById("btnMenu")?.addEventListener("click", openDrawer);
  document.getElementById("drawerOverlay")?.addEventListener("click", closeDrawer);
  document.querySelectorAll("#drawer a").forEach(a => a.addEventListener("click", closeDrawer));

  // refresh
  document.getElementById("btnRefresh")?.addEventListener("click", () => location.reload());

  // bottom nav routing
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const k = item.dataset.key;
      if (!FEATURES[k]) return;

      setActiveNavByKey(k);
      setTopbarTitle(item.dataset.title);

      const route = ROUTES[k];
      if (route) window.location.href = route;
    });
  });
}

document.addEventListener("DOMContentLoaded", initShell);
