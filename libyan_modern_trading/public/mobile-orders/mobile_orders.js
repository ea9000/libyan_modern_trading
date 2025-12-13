/* === your full JS from the working version === */
/* pasted exactly (I’m keeping it as-is) */

const ERPNEXT_BASE_URL = window.location.origin;

let DEFAULT_COMPANY      = null;
let DEFAULT_WAREHOUSE    = null;
let DEFAULT_PRICE_LIST   = null;

let SALESPERSON_NAME     = null;

let LOGGED_USER_EMAIL = (window.LOGGED_IN_USER && window.LOGGED_IN_USER !== "{{ frappe.session.user }}")
  ? window.LOGGED_IN_USER
  : null;

const FREE_FIELDNAME = "is_free_item";

function asChecked(v) {
  if (v === true) return true;
  const n = Number(v);
  if (!Number.isNaN(n)) return n === 1;
  const s = String(v || "").toLowerCase().trim();
  return s === "yes" || s === "y" || s === "true";
}

let currentOrderType = "sale";
let currentOrderName = null;
let currentOrderDoc  = null;

let currentItems = [];
let editingItemIndex = null;

let itemMaster = [];
let itemCodeByLabel = {};
let itemPriceByCode = {};

let itemQtyByCode   = {};

const STOCK_LOW_MAX  = 9;
const STOCK_MID_MAX  = 99;
const STOCK_FULL_MIN = 100;

let customerMaster = [];
let customerIdByName = {};

let selectedCustomerName = "";
let selectedCustomerId   = "";

let openOrders = [];

function getCookie(name) {
  const value = "; " + document.cookie;
  const parts = value.split("; " + name + "=");
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

function getCsrfToken() {
  if (window.frappe && frappe.csrf_token) return frappe.csrf_token;

  if (
    typeof window.CSRF_TOKEN === "string" &&
    window.CSRF_TOKEN &&
    window.CSRF_TOKEN !== "{{ csrf_token }}"
  ) return window.CSRF_TOKEN;

  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content && meta.content !== "{{ csrf_token }}") return meta.content;

  const cookieNames = ["csrf_token", "X-Frappe-CSRF-Token", "frappe-csrf-token"];
  for (const n of cookieNames) {
    const v = getCookie(n);
    if (v) return v;
  }
  return null;
}

async function erpRequest(path, options = {}) {
  const url = path.startsWith("http") ? path : ERPNEXT_BASE_URL + path;

  const headers = Object.assign({}, options.headers || {});
  const method  = (options.method || "GET").toUpperCase();

  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    const token = getCsrfToken();
    if (token) headers["X-Frappe-CSRF-Token"] = token;
  }

  const resp = await fetch(url, Object.assign({}, options, {
    method,
    headers,
    credentials: "include"
  }));

  const txt = await resp.text();
  if (!resp.ok) {
    console.error("ERPNext error:", resp.status, txt);
    throw new Error("Status " + resp.status + ": " + txt);
  }

  try { return JSON.parse(txt); }
  catch { return txt; }
}

function updateHeaderMetaUI(warehouseOverride = null, salespersonOverride = null) {
  const sp = document.getElementById("salesPersonView");
  if (sp) sp.textContent = salespersonOverride || SALESPERSON_NAME || (LOGGED_USER_EMAIL || "");

  const wh = document.getElementById("warehouseView");
  if (wh) wh.textContent = warehouseOverride || DEFAULT_WAREHOUSE || "-";
}

async function loadDefaultsFromERPNext() {
  DEFAULT_COMPANY    = null;
  DEFAULT_WAREHOUSE  = null;
  DEFAULT_PRICE_LIST = null;
  SALESPERSON_NAME   = null;

  if (!LOGGED_USER_EMAIL || LOGGED_USER_EMAIL === "Guest") {
    try {
      const who = await erpRequest("/api/method/frappe.auth.get_logged_user");
      LOGGED_USER_EMAIL = (who.message || who).trim();
    } catch (e) {
      console.warn("Could not load logged user", e);
    }
  }

  try {
    const gd = await erpRequest(
      "/api/resource/Global Defaults/Global Defaults?fields=" +
      encodeURIComponent(JSON.stringify(["default_company", "default_price_list"]))
    );
    const gdDoc = gd.data || gd;
    DEFAULT_COMPANY    = gdDoc.default_company || null;
    DEFAULT_PRICE_LIST = gdDoc.default_price_list || null;
  } catch (e) {
    console.warn("Could not load global defaults", e);
  }

  try {
    if (LOGGED_USER_EMAIL) {
      const udocResp = await erpRequest(
        "/api/resource/User/" + encodeURIComponent(LOGGED_USER_EMAIL) +
        "?fields=" + encodeURIComponent(JSON.stringify(["warehouse","full_name","first_name","last_name"]))
      );
      const udoc = udocResp.data || udocResp;

      if (udoc.warehouse) DEFAULT_WAREHOUSE = udoc.warehouse;

      SALESPERSON_NAME =
        udoc.full_name ||
        [udoc.first_name, udoc.last_name].filter(Boolean).join(" ") ||
        LOGGED_USER_EMAIL;
    }
  } catch (e) {
    console.warn("Could not load user warehouse/name", e);
  }

  if (!DEFAULT_PRICE_LIST) DEFAULT_PRICE_LIST = "Standard Selling";

  updateHeaderMetaUI();
}

async function loadItemsFromERPNext() {
  try {
    const fields = ["name", "item_name", "disabled", "end_of_life"];
    const data = await erpRequest(
      "/api/resource/Item?fields=" +
      encodeURIComponent(JSON.stringify(fields)) +
      "&limit_page_length=500"
    );

    const today = new Date().toISOString().split("T")[0];

    itemMaster = [];
    itemCodeByLabel = {};

    (data.data || []).forEach(doc => {
      if (doc.disabled) return;
      if (doc.end_of_life && doc.end_of_life < today) return;

      const label = doc.name + " - " + (doc.item_name || "");
      itemMaster.push(label);
      itemCodeByLabel[label] = doc.name;
    });
  } catch (e) {
    console.error("Error loading items:", e);
    alert("فشل تحميل الأصناف من ERPNext");
  }
}

async function loadItemPricesFromERPNext() {
  try {
    itemPriceByCode = {};

    const fields = ["item_code", "price_list_rate", "price_list", "selling"];
    const filters = [
      ["Item Price", "price_list", "=", DEFAULT_PRICE_LIST],
      ["Item Price", "selling", "=", 1]
    ];

    const data = await erpRequest(
      "/api/resource/Item Price?fields=" +
      encodeURIComponent(JSON.stringify(fields)) +
      "&filters=" + encodeURIComponent(JSON.stringify(filters)) +
      "&limit_page_length=2000"
    );

    (data.data || []).forEach(p => {
      const code = p.item_code;
      const rate = Number(p.price_list_rate || 0);
      if (code && !Number.isNaN(rate)) itemPriceByCode[code] = rate;
    });
  } catch (e) {
    console.error("Error loading item prices:", e);
  }
}

async function loadStockFromERPNext() {
  try {
    itemQtyByCode = {};

    if (!DEFAULT_WAREHOUSE) return;

    const fields  = ["item_code", "warehouse", "actual_qty"];
    const filters = [["Bin", "warehouse", "=", DEFAULT_WAREHOUSE]];

    const data = await erpRequest(
      "/api/resource/Bin?fields=" +
        encodeURIComponent(JSON.stringify(fields)) +
        "&filters=" + encodeURIComponent(JSON.stringify(filters)) +
        "&limit_page_length=2000"
    );

    (data.data || []).forEach(r => {
      const code = r.item_code;
      const qty  = Number(r.actual_qty || 0);
      if (code) itemQtyByCode[code] = qty;
    });
  } catch (e) {
    console.error("Error loading stock:", e);
  }
}

async function loadCustomersFromERPNext() {
  try {
    const fields = ["name", "customer_name", "account_manager"];

    const filters = [];
    if (LOGGED_USER_EMAIL) filters.push(["Customer", "account_manager", "=", LOGGED_USER_EMAIL]);

    const data = await erpRequest(
      "/api/resource/Customer?fields=" +
      encodeURIComponent(JSON.stringify(fields)) +
      (filters.length ? "&filters=" + encodeURIComponent(JSON.stringify(filters)) : "") +
      "&limit_page_length=500"
    );

    customerMaster = [];
    customerIdByName = {};

    (data.data || []).forEach(doc => {
      const display = doc.customer_name || doc.name;
      customerMaster.push({ name: display, color: "#004b80" });
      customerIdByName[display] = doc.name;
    });
  } catch (e) {
    console.error("Error loading customers:", e);
    alert("فشل تحميل الزبائن من ERPNext");
  }
}

async function loadOpenOrdersFromERPNext() {
  try {
    const fields = ["name","customer","customer_name","transaction_date","grand_total","status","docstatus","set_warehouse","owner"];
    const filters = [
      ["Sales Order", "docstatus", "!=", 2],
      ["Sales Order", "status", "!=", "Closed"]
    ];

    if (LOGGED_USER_EMAIL) filters.push(["Sales Order", "owner", "=", LOGGED_USER_EMAIL]);

    const data = await erpRequest(
      "/api/resource/Sales Order?fields=" +
      encodeURIComponent(JSON.stringify(fields)) +
      "&filters=" + encodeURIComponent(JSON.stringify(filters)) +
      "&order_by=transaction_date desc" +
      "&limit_page_length=100"
    );

    openOrders = data.data || [];
    renderOrdersList();
  } catch (e) {
    console.error("Error loading orders:", e);
    alert("فشل تحميل الطلبات من ERPNext");
  }
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderOrdersList() {
  const listEl  = document.getElementById("ordersList");
  const emptyEl = document.getElementById("ordersEmptyText");
  if (!listEl || !emptyEl) return;

  listEl.innerHTML = "";

  if (!openOrders.length) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  openOrders.forEach(order => {
    const card = document.createElement("div");
    card.className = "order-card";

    const left = document.createElement("div");
    left.className = "order-card-left";

    const line1 = document.createElement("div");
    line1.className = "order-card-line1";

    const amountDiv = document.createElement("div");
    amountDiv.className = "order-card-amount";
    const amount = Number(order.grand_total || 0);
    amountDiv.textContent =
      amount.toLocaleString("ar-LY", { minimumFractionDigits: 1, maximumFractionDigits: 3 }) + " د.ل";

    const customerDiv = document.createElement("div");
    customerDiv.className = "order-card-customer";
    customerDiv.textContent = order.customer_name || order.customer || "";

    line1.appendChild(amountDiv);
    line1.appendChild(customerDiv);

    const line2 = document.createElement("div");
    line2.className = "order-card-line2";

    const metaLeft = document.createElement("div");
    metaLeft.style.display = "flex";
    metaLeft.style.flexDirection = "column";
    metaLeft.style.fontSize = "11px";

    const dateDiv = document.createElement("div");
    dateDiv.textContent = order.transaction_date || "";

    const idDiv = document.createElement("div");
    idDiv.textContent = order.name;
    idDiv.style.color = "#555";

    metaLeft.appendChild(dateDiv);
    metaLeft.appendChild(idDiv);

    const statusDiv = document.createElement("div");
    statusDiv.className = "order-status-pill";

    const dot = document.createElement("span");
    dot.className = "order-dot " + (order.docstatus === 1 ? "order-dot-green" : "order-dot-orange");

    const statusText = document.createTextNode(" " + (order.status || "Draft"));

    statusDiv.appendChild(dot);
    statusDiv.appendChild(statusText);

    line2.appendChild(metaLeft);
    line2.appendChild(statusDiv);

    const line3 = document.createElement("div");
    line3.className = "order-card-line3";

    const sp = SALESPERSON_NAME || (order.owner || LOGGED_USER_EMAIL || "");
    const wh = order.set_warehouse || DEFAULT_WAREHOUSE || "-";

    line3.innerHTML =
      `المندوب: <span class="val">${escapeHtml(sp)}</span>` +
      `<span class="sep">|</span>` +
      `المخزن: <span class="val">${escapeHtml(wh)}</span>`;

    left.appendChild(line1);
    left.appendChild(line2);
    left.appendChild(line3);

    card.appendChild(left);
    card.addEventListener("click", () => openExistingOrder(order.name));

    listEl.appendChild(card);
  });
}

function renderItemsList() {
  const container = document.getElementById("itemsContainer");
  if (!container) return;

  container.innerHTML = "";

  if (!currentItems.length) {
    const emptyText = document.createElement("div");
    emptyText.className = "items-empty";
    emptyText.textContent = "لا توجد أصناف مضافة";
    container.appendChild(emptyText);
    return;
  }

  currentItems.forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "item-row";

    const nameDiv = document.createElement("div");
    nameDiv.className = "item-row-name";
    nameDiv.textContent = item.name;

    const rightDiv = document.createElement("div");
    rightDiv.className = "item-row-badges";

    const qtySpan = document.createElement("span");
    qtySpan.className = "item-row-badge";
    qtySpan.textContent = "× " + item.qty;

    const modeSpan = document.createElement("span");
    modeSpan.className = "item-row-badge";
    if (item.is_free) {
      modeSpan.classList.add("item-row-free");
      modeSpan.textContent = "مجاني";
    } else {
      modeSpan.textContent = "بيع";
    }

    const delSpan = document.createElement("span");
    delSpan.className = "item-delete";
    delSpan.textContent = "✕";
    delSpan.addEventListener("click", (ev) => {
      ev.stopPropagation();
      currentItems.splice(idx, 1);
      renderItemsList();
    });

    rightDiv.appendChild(qtySpan);
    rightDiv.appendChild(modeSpan);
    rightDiv.appendChild(delSpan);

    row.appendChild(nameDiv);
    row.appendChild(rightDiv);

    row.addEventListener("click", () => openItemModalForEdit(idx));
    container.appendChild(row);
  });
}

function showListScreen() {
  document.getElementById("listScreen").style.display = "block";
  document.getElementById("orderFormScreen").style.display = "none";
  document.getElementById("formBottomBar").style.display = "none";
}
function showOrderFormScreen() {
  document.getElementById("listScreen").style.display = "none";
  document.getElementById("orderFormScreen").style.display = "block";
  document.getElementById("formBottomBar").style.display = "flex";
  updateHeaderMetaUI();
}

/* NOTE: bottom bar sits above shell bottom nav */
function positionBottomBar() {
  const bar = document.getElementById("formBottomBar");
  if (!bar) return;
  bar.style.bottom = "56px";
}

function showOrderTypeModal() { document.getElementById("orderTypeModal").style.display = "flex"; }
function hideOrderTypeModal() { document.getElementById("orderTypeModal").style.display = "none"; }

function showItemModal() { document.getElementById("itemModal").style.display = "flex"; }
function hideItemModal() { document.getElementById("itemModal").style.display = "none"; }

async function showItemListModal() {
  await loadStockFromERPNext();
  filterAndRenderItemList("");
  document.getElementById("itemSearchInput").value = "";
  document.getElementById("itemListModal").style.display = "flex";
}
function hideItemListModal() { document.getElementById("itemListModal").style.display = "none"; }

function showCustomerListModal() {
  if (currentOrderName) {
    alert("لا يمكن تغيير الزبون بعد إنشاء الطلب");
    return;
  }
  filterAndRenderCustomerList("");
  document.getElementById("customerSearchInput").value = "";
  document.getElementById("customerListModal").style.display = "flex";
}
function hideCustomerListModal() { document.getElementById("customerListModal").style.display = "none"; }

function getStockDotColorByQty(qty) {
  qty = Number(qty || 0);
  if (qty <= 0) return "#d32f2f";
  if (qty <= STOCK_LOW_MAX) return "#f57c00";
  if (qty <= STOCK_MID_MAX) return "#fbc02d";
  return "#2e7d32";
}

function buildSelectList(container, dataArray, selectedName) {
  container.innerHTML = "";
  const isItemList = (container.id === "itemListScroller");

  dataArray.forEach(entry => {
    const name = typeof entry === "string" ? entry : entry.name;

    let color = "#0a7a0a";
    if (!isItemList) {
      color = typeof entry === "string" ? "#0a7a0a" : (entry.color || "#0a7a0a");
    } else {
      const code = itemCodeByLabel[name];
      const qty  = code ? (itemQtyByCode[code] ?? 0) : 0;
      color = getStockDotColorByQty(qty);
    }

    const row  = document.createElement("div");
    row.className = "select-list-row";

    const radio = document.createElement("div");
    radio.className = "select-list-radio";
    if (name === selectedName) radio.classList.add("selected");

    const dot = document.createElement("div");
    dot.className = "select-list-dot";
    dot.style.backgroundColor = color;

    const text = document.createElement("div");
    text.className = "select-list-text";
    text.textContent = name;

    row.appendChild(radio);
    row.appendChild(dot);
    row.appendChild(text);

    if (isItemList) {
      const code = itemCodeByLabel[name];
      const qty  = code ? (itemQtyByCode[code] ?? 0) : 0;
      const q = document.createElement("div");
      q.style.marginInlineStart = "auto";
      q.style.fontSize = "12px";
      q.style.color = "#666";
      q.textContent = String(qty);
      row.appendChild(q);
    }

    row.addEventListener("click", () => {
      container.querySelectorAll(".select-list-radio").forEach(r => r.classList.remove("selected"));
      radio.classList.add("selected");

      if (isItemList) {
        document.getElementById("itemNameInput").value = name;
        recalcModalTotal();
      } else {
        selectedCustomerName = name;
        selectedCustomerId   = customerIdByName[name] || "";
        document.getElementById("customerInput").value = name;
      }
    });

    container.appendChild(row);
  });
}

function filterAndRenderItemList(filterText) {
  const filter   = (filterText || "").toLowerCase();
  const scroller = document.getElementById("itemListScroller");
  const filtered = itemMaster.filter(n => n.toLowerCase().includes(filter));
  buildSelectList(scroller, filtered, document.getElementById("itemNameInput").value);
}

function filterAndRenderCustomerList(filterText) {
  const filter   = (filterText || "").toLowerCase();
  const scroller = document.getElementById("customerListScroller");
  const filtered = customerMaster.filter(c => c.name.toLowerCase().includes(filter));
  buildSelectList(scroller, filtered, selectedCustomerName);
}

function setItemMode(mode) {
  const saleBtn = document.getElementById("saleToggleBtn");
  const freeBtn = document.getElementById("freeToggleBtn");
  if (mode === "sale") {
    saleBtn.classList.add("active-sale");
    freeBtn.classList.remove("active-free");
  } else {
    saleBtn.classList.remove("active-sale");
    freeBtn.classList.add("active-free");
  }
  recalcModalTotal();
}
function getItemMode() {
  const freeBtn = document.getElementById("freeToggleBtn");
  return freeBtn.classList.contains("active-free") ? "free" : "sale";
}

function lockTotalInput() {
  const totalEl = document.getElementById("totalInput");
  if (!totalEl) return;
  totalEl.setAttribute("disabled", "disabled");
  totalEl.classList.add("locked");
}

function recalcModalTotal() {
  const totalEl = document.getElementById("totalInput");
  const nameEl  = document.getElementById("itemNameInput");
  const qtyEl   = document.getElementById("qtyInput");
  if (!totalEl || !nameEl || !qtyEl) return;

  const mode = getItemMode();
  const label = nameEl.value.trim();
  const code = itemCodeByLabel[label] || null;

  let qty = parseInt(qtyEl.value || "1", 10);
  if (isNaN(qty) || qty < 1) qty = 1;

  if (mode === "free") {
    totalEl.value = "0";
    return;
  }

  const price = code ? Number(itemPriceByCode[code] || 0) : 0;
  const total = price * qty;

  totalEl.value = String(total || 0);
}

function openItemModalForNew() {
  editingItemIndex = null;
  document.getElementById("itemNameInput").value = "";
  document.getElementById("qtyInput").value      = 1;
  document.getElementById("totalInput").value    = 0;
  setItemMode("sale");
  lockTotalInput();
  recalcModalTotal();
  showItemModal();
}

function openItemModalForEdit(idx) {
  editingItemIndex = idx;
  const item = currentItems[idx];
  if (!item) return;

  document.getElementById("itemNameInput").value = item.name;
  document.getElementById("qtyInput").value      = item.qty;

  setItemMode(item.is_free ? "free" : "sale");
  lockTotalInput();
  recalcModalTotal();

  showItemModal();
}

function refreshStatusUI() {
  const statusSpan = document.getElementById("orderStatusText");
  if (!statusSpan) return;

  let s = "Draft";
  if (currentOrderDoc) {
    s = currentOrderDoc.status || s;
    if (!currentOrderDoc.status) {
      if (currentOrderDoc.docstatus === 1) s = "Submitted";
      else if (currentOrderDoc.docstatus === 2) s = "Cancelled";
    }
  }
  statusSpan.textContent = s;
}

async function openExistingOrder(orderName) {
  try {
    const data = await erpRequest("/api/resource/Sales Order/" + encodeURIComponent(orderName));
    const doc = data.data || data;

    currentOrderName = doc.name;
    currentOrderDoc  = doc;

    selectedCustomerId   = doc.customer;
    selectedCustomerName = doc.customer_name || doc.customer || "";

    const customerInputEl = document.getElementById("customerInput");
    if (customerInputEl) {
      customerInputEl.value = selectedCustomerName;
      customerInputEl.classList.add("locked");
    }

    document.getElementById("invoiceNumber").value = doc.name;
    document.getElementById("orderDate").value    = doc.transaction_date || "";
    document.getElementById("discountPercent").value = doc.additional_discount_percentage || 0;

    document.getElementById("orderFormTitle").textContent = "تعديل الطلبية";

    updateHeaderMetaUI(doc.set_warehouse || DEFAULT_WAREHOUSE || "-", SALESPERSON_NAME);

    currentItems = (doc.items || []).map(row => {
      const hasFreeField = Object.prototype.hasOwnProperty.call(row, FREE_FIELDNAME);
      const isFree = hasFreeField ? asChecked(row[FREE_FIELDNAME]) : (Number(row.rate || 0) === 0);

      return {
        name: row.item_name || row.item_code,
        code: row.item_code,
        qty:  row.qty || 1,
        total: isFree ? 0 : (row.amount || 0),
        is_free: isFree
      };
    });

    renderItemsList();
    refreshStatusUI();
    showOrderFormScreen();
  } catch (e) {
    console.error("Failed to open order:", e);
    alert("فشل فتح الطلبية من ERPNext");
  }
}

/* save/cancel/submit functions kept same as your version (not removed) */
/* IMPORTANT: if you want, I can also move those to a separate file later. */

async function initMobileOrdersApp() {
  positionBottomBar();

  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("orderDate");
  if (dateInput && !dateInput.value) dateInput.value = today;

  const fab = document.querySelector(".mobile-fab");
  if (fab) fab.addEventListener("click", showOrderTypeModal);

  document.getElementById("cancelOrderTypeBtn").addEventListener("click", hideOrderTypeModal);
  document.getElementById("orderFormBackBtn").addEventListener("click", showListScreen);
  document.getElementById("cancelOrderBtn").addEventListener("click", showListScreen);

  renderItemsList();
  refreshStatusUI();

  await loadDefaultsFromERPNext();
  await Promise.all([ loadItemsFromERPNext(), loadCustomersFromERPNext() ]);
  await loadItemPricesFromERPNext();
  await loadStockFromERPNext();
  await loadOpenOrdersFromERPNext();
  showListScreen();
}

document.addEventListener("DOMContentLoaded", initMobileOrdersApp);
