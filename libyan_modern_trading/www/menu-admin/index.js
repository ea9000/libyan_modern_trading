const API = {
  list: "/api/method/libyan_modern_trading.api.menu_admin.list_menu_items",
  get: "/api/method/libyan_modern_trading.api.menu_admin.get_menu_item",
  save: "/api/method/libyan_modern_trading.api.menu_admin.save_menu_item",
  del: "/api/method/libyan_modern_trading.api.menu_admin.delete_menu_item",
  roles: "/api/method/libyan_modern_trading.api.menu_admin.list_roles",
  users: "/api/method/libyan_modern_trading.api.menu_admin.list_users",
};

let items = [];
let current = null;

function $(id){ return document.getElementById(id); }

async function call(url, args={}) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(args)
  });
  const j = await r.json();
  if (j.exc) throw new Error("Server error");
  return j.message;
}

function msg(t){ $("msg").textContent = t || ""; }

function renderList(filter="") {
  const list = $("itemsList");
  list.innerHTML = "";
  const f = (filter||"").toLowerCase();

  items
    .filter(x => {
      const a = (x.title_ar||"").toLowerCase();
      const b = (x.title_en||"").toLowerCase();
      const c = (x.route||"").toLowerCase();
      return !f || a.includes(f) || b.includes(f) || c.includes(f);
    })
    .forEach(x => {
      const div = document.createElement("div");
      div.className = "ma-item" + (current && current.name === x.name ? " active" : "");
      div.innerHTML = `<div class="t">${x.title_ar || "(no title)"}</div><div class="s">${x.route || ""}</div>`;
      div.onclick = () => loadItem(x.name);
      list.appendChild(div);
    });
}

function setMultiSelect(selectEl, values) {
  const set = new Set(values || []);
  [...selectEl.options].forEach(o => o.selected = set.has(o.value));
}

function getMultiSelect(selectEl) {
  return [...selectEl.selectedOptions].map(o => o.value);
}

function fillForm(d) {
  current = d;

  $("title_ar").value = d.title_ar || "";
  $("title_en").value = d.title_en || "";
  $("route").value = d.route || "";
  $("sort_order").value = d.sort_order ?? 10;

  $("is_active").checked = !!d.is_active;
  $("show_on_home_grid").checked = !!d.show_on_home_grid;
  $("show_on_bottom_nav").checked = !!d.show_on_bottom_nav;
  $("open_in_new_tab").checked = !!d.open_in_new_tab;

  $("icon_type").value = d.icon_type || "Emoji";
  $("emoji").value = d.emoji || "";
  $("fa_class").value = d.fa_class || "";
  $("image_url").value = d.image_url || "";

  const roles = (d.allowed_roles || []).map(r => r.role).filter(Boolean);
  const users = (d.allowed_users || []).map(u => u.user).filter(Boolean);

  setMultiSelect($("rolesSelect"), roles);
  setMultiSelect($("usersSelect"), users);

  renderList($("search").value);
}

function newItem() {
  fillForm({
    name: null,
    title_ar: "",
    title_en: "",
    route: "",
    sort_order: 10,
    is_active: 1,
    show_on_home_grid: 1,
    show_on_bottom_nav: 0,
    open_in_new_tab: 0,
    icon_type: "Emoji",
    emoji: "🏠",
    fa_class: "",
    image_url: "",
    allowed_roles: [],
    allowed_users: []
  });
  msg("New item (not saved)");
}

async function loadItem(name) {
  msg("");
  const d = await call(API.get, {name});
  fillForm(d);
}

async function reloadAll() {
  msg("");
  items = await call(API.list);
  renderList($("search").value);
}

async function loadRoleUserOptions() {
  const roles = await call(API.roles);
  const users = await call(API.users);

  $("rolesSelect").innerHTML = roles.map(r => `<option value="${r}">${r}</option>`).join("");
  $("usersSelect").innerHTML = users.map(u => `<option value="${u}">${u}</option>`).join("");
}

async function saveCurrent() {
  msg("");
  const d = {
    name: current && current.name ? current.name : undefined,
    title_ar: $("title_ar").value.trim(),
    title_en: $("title_en").value.trim(),
    route: $("route").value.trim(),
    sort_order: parseInt($("sort_order").value || "10", 10),
    is_active: $("is_active").checked ? 1 : 0,
    show_on_home_grid: $("show_on_home_grid").checked ? 1 : 0,
    show_on_bottom_nav: $("show_on_bottom_nav").checked ? 1 : 0,
    open_in_new_tab: $("open_in_new_tab").checked ? 1 : 0,
    icon_type: $("icon_type").value,
    emoji: $("emoji").value.trim(),
    fa_class: $("fa_class").value.trim(),
    image_url: $("image_url").value.trim(),
    allowed_roles: getMultiSelect($("rolesSelect")).map(r => ({role: r})),
    allowed_users: getMultiSelect($("usersSelect")).map(u => ({user: u})),
  };

  const res = await call(API.save, {doc: d});
  msg("Saved: " + res.name);
  await reloadAll();
  if (res.name) await loadItem(res.name);
}

async function deleteCurrent() {
  if (!current || !current.name) return msg("Nothing to delete.");
  await call(API.del, {name: current.name});
  msg("Deleted.");
  current = null;
  await reloadAll();
  newItem();
}

document.addEventListener("DOMContentLoaded", async () => {
  $("btnNew").onclick = newItem;
  $("btnReload").onclick = reloadAll;
  $("btnSave").onclick = saveCurrent;
  $("btnDelete").onclick = deleteCurrent;
  $("search").oninput = () => renderList($("search").value);

  await loadRoleUserOptions();
  await reloadAll();
  newItem();
});
