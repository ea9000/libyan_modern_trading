// ================= API =================
async function fetchMenu() {
  const r = await fetch("/api/method/libyan_modern_trading.api.menu.list_menu_items", {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "same-origin"
  });
  const data = await r.json();
  if (!data || !data.message) return [];
  return data.message;
}

function iconHtml(it) {
  if (it.icon_type === "FontAwesome" && it.fa_class) return `<i class="${it.fa_class}"></i>`;
  if (it.icon_type === "ImageURL" && it.image_url) return `<img src="${it.image_url}" style="width:28px;height:28px;object-fit:contain;">`;
  return (it.emoji || "⬜");
}

function setTopbarTitle(title) {
  const el = document.getElementById("topbarTitle");
  if (el) el.textContent = title || "";
}

// ================= RENDER =================
function renderGrid(items) {
  const grid = document.querySelector(".home-grid");
  if (!grid) return;

  const homeItems = items.filter(x => x.show_on_home_grid);
  grid.innerHTML = "";

  homeItems.forEach(it => {
    const card = document.createElement("div");
    card.className = "card";
    card.onclick = () => (window.location.href = it.route);

    card.innerHTML = `
      <div class="card-icon">${iconHtml(it)}</div>
      <div class="card-title">${it.title_ar || it.title_en || it.name}</div>
      <div class="card-sub">${it.route || ""}</div>
    `;
    grid.appendChild(card);
  });
}

function renderBottomNav(items) {
  const nav = document.getElementById("bottomNav");
  if (!nav) return;

  const navItems = items.filter(x => x.show_on_bottom_nav);
  nav.innerHTML = "";

  navItems.forEach(it => {
    const div = document.createElement("div");
    div.className = "nav-item";
    div.innerHTML = `${iconHtml(it)}<br>${it.title_ar || it.title_en || it.name}`;
    div.onclick = () => (window.location.href = it.route);
    nav.appendChild(div);
  });
}

// ================= INIT =================
async function initHome() {
  try {
    const items = await fetchMenu();

    // DEBUG PROOF in console
    console.log("LMT menu items from DocType:", items);

    // optional: set title to first item group or keep existing title
    // setTopbarTitle("الرئيسية");

    renderGrid(items);
    renderBottomNav(items);
  } catch (e) {
    console.error("Menu load failed:", e);
  }

  const refreshBtn = document.getElementById("btnRefresh");
  if (refreshBtn) refreshBtn.onclick = () => location.reload();
}

document.addEventListener("DOMContentLoaded", initHome);
