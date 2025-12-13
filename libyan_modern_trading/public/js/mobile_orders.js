// ================= SESSION-BASED CONFIG =================
const ERPNEXT_BASE_URL = window.location.origin;

// Per-user defaults
let DEFAULT_COMPANY      = null;
let DEFAULT_WAREHOUSE    = null;
let DEFAULT_PRICE_LIST   = null;

// ✅ NEW: sales person display name
let SALESPERSON_NAME     = null;

// use ERPNext session user injected by Jinja if available
let LOGGED_USER_EMAIL = (window.LOGGED_IN_USER && window.LOGGED_IN_USER !== "{{ frappe.session.user }}")
  ? window.LOGGED_IN_USER
  : null;

// ✅ Custom fieldname on Sales Order Item
const FREE_FIELDNAME = "is_free_item";

// ✅ checkbox values may come as 0/1 or "0"/"1" or true/false
function asChecked(v) {
  if (v === true) return true;
  const n = Number(v);
  if (!Number.isNaN(n)) return n === 1;
  const s = String(v || "").toLowerCase().trim();
  return s === "yes" || s === "y" || s === "true";
}

// ================ GLOBAL STATE ================
let currentOrderType = "sale";
let currentOrderName = null;
let currentOrderDoc  = null;

let currentItems = [];
let editingItemIndex = null;

let itemMaster = [];
let itemCodeByLabel = {};
let itemPriceByCode = {};

// ✅ Inventory map (Bin)
let itemQtyByCode   = {};

// ✅ Thresholds like AppSheet rules
const STOCK_LOW_MAX  = 9;
const STOCK_MID_MAX  = 99;
const STOCK_FULL_MIN = 100;

let customerMaster = [];
let customerIdByName = {};

let selectedCustomerName = "";
let selectedCustomerId   = "";

let openOrders = [];

// ============= COOKIE / CSRF HELPERS =============
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

// ============= ERP REQUEST HELPER (SESSION) =============
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

// ✅ Update UI for salesperson + warehouse (DETAIL VIEW)
function updateHeaderMetaUI(warehouseOverride = null, salespersonOverride = null) {
  const sp = document.getElementById("salesPersonView");
  if (sp) sp.textContent = salespersonOverride || SALESPERSON_NAME || (LOGGED_USER_EMAIL || "");

  const wh = document.getElementById("warehouseView");
  if (wh) wh.textContent = warehouseOverride || DEFAULT_WAREHOUSE || "-";
}

// ============= LOAD DEFAULTS (company / warehouse / price list / user) =============
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

  // Global Defaults (company + price list)
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

  // ✅ User warehouse + display name
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

  console.log("Defaults:", { DEFAULT_COMPANY, DEFAULT_WAREHOUSE, DEFAULT_PRICE_LIST, LOGGED_USER_EMAIL, SALESPERSON_NAME });

  updateHeaderMetaUI();
}

// ============= LOAD MASTER DATA =============
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

    console.log("Loaded items:", itemMaster.length);
  } catch (e) {
    console.error("Error loading items:", e);
    alert("فشل تحميل الأصناف من ERPNext");
  }
}

// ✅ Load prices
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

    console.log("Loaded item prices:", Object.keys(itemPriceByCode).length, "for price list:", DEFAULT_PRICE_LIST);
  } catch (e) {
    console.error("Error loading item prices:", e);
    console.warn("Could not load Item Price; sales totals may be 0 if price missing.");
  }
}

// ✅ Load stock from Bin for DEFAULT_WAREHOUSE
async function loadStockFromERPNext() {
  try {
    itemQtyByCode = {};

    if (!DEFAULT_WAREHOUSE) {
      console.warn("No DEFAULT_WAREHOUSE. Stock dots disabled.");
      return;
    }

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

    console.log("Loaded stock for warehouse:", DEFAULT_WAREHOUSE, "items:", Object.keys(itemQtyByCode).length);
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

    console.log("Loaded customers:", customerMaster.length);
  } catch (e) {
    console.error("Error loading customers:", e);
    alert("فشل تحميل الزبائن من ERPNext");
  }
}

async function loadOpenOrdersFromERPNext() {
  try {
    // ✅ include set_warehouse + owner so we can show warehouse/salesperson in list
    const fields = ["name","customer","customer_name","transaction_date","grand_total","status","docstatus","set_warehouse","owner"];

    const filters = [
      ["Sales Order", "docstatus", "!=", 2],
      ["Sales Order", "status", "!=", "Closed"]
    ];

    if (LOGGED_USER_EMAIL) filters.push(["Sales Order", "owner", "=", LOGGED_USER_EMAIL]);

    const data = await erpRequest(
      "/api/resource/Sales Order?fields=" +
      encodeURIComponent(JSON.stringify(fields)) +
      "&filters=" +
      encodeURIComponent(JSON.stringify(filters)) +
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

// ============= RENDER ORDERS LIST =============
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

    // ✅ NEW: salesperson + warehouse in list card
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

// small helper to avoid breaking HTML if names contain special chars
function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ============= ITEMS RENDER =============
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

// ============= MODAL HELPERS =============
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

// ============= SELECT LISTS (ITEM & CUSTOMER) =============
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

// ============= ITEM MODAL (NEW / EDIT) =============
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

// ============= STATUS UI HELPER =============
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

// ============= OPEN EXISTING ORDER =============
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

    // ✅ show warehouse from order if exists
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

// ============= SAVE ORDER (NEW + UPDATE) =============
async function saveOrderToERPNext() {
  try {
    if (!selectedCustomerName && !selectedCustomerId) {
      alert("الرجاء اختيار الزبون");
      return;
    }
    if (!currentItems.length) {
      alert("الرجاء إضافة أصناف");
      return;
    }

    const dateStr = document.getElementById("orderDate").value;
    if (!dateStr) {
      alert("الرجاء اختيار تاريخ الطلب");
      return;
    }

    const disc = parseFloat(document.getElementById("discountPercent").value || "0") || 0;

    const itemsPayload = currentItems.map((it, idx) => {
      const qty  = it.qty || 1;
      const code = it.code || itemCodeByLabel[it.name] || undefined;

      if (it.is_free) {
        return {
          doctype: "Sales Order Item",
          idx: idx + 1,
          item_code: code,
          item_name: it.name,
          qty,
          price_list_rate: 0,
          rate: 0,
          amount: 0,
          [FREE_FIELDNAME]: 1,
          warehouse: DEFAULT_WAREHOUSE || undefined
        };
      }

      const price  = code ? Number(itemPriceByCode[code] || 0) : 0;
      const rate   = price;
      const amount = rate * qty;

      return {
        doctype: "Sales Order Item",
        idx: idx + 1,
        item_code: code,
        item_name: it.name,
        qty,
        price_list_rate: rate,
        rate: rate,
        amount: amount,
        [FREE_FIELDNAME]: 0,
        warehouse: DEFAULT_WAREHOUSE || undefined
      };
    });

    const hasZeroSale = itemsPayload.some(r => !r[FREE_FIELDNAME] && Number(r.rate || 0) === 0);
    if (hasZeroSale) {
      if (!confirm("يوجد صنف (بيع) بدون سعر في قائمة الأسعار. سيتم حفظه بسعر 0. هل تريد المتابعة؟")) return;
    }

    if (!currentOrderName) {
      const doc = {
        doctype: "Sales Order",
        customer: selectedCustomerId || selectedCustomerName,
        transaction_date: dateStr,
        delivery_date: dateStr,
        additional_discount_percentage: disc,
        ignore_pricing_rule: 1,
        items: itemsPayload
      };

      if (DEFAULT_COMPANY)    doc.company = DEFAULT_COMPANY;
      if (DEFAULT_WAREHOUSE)  doc.set_warehouse = DEFAULT_WAREHOUSE;
      if (DEFAULT_PRICE_LIST) doc.selling_price_list = DEFAULT_PRICE_LIST;

      const resp = await erpRequest("/api/resource/Sales Order", {
        method: "POST",
        body: JSON.stringify(doc)
      });

      const saved = resp.data || resp;
      currentOrderName = saved.name;
      currentOrderDoc  = saved;
      document.getElementById("invoiceNumber").value = saved.name;

      updateHeaderMetaUI(saved.set_warehouse || DEFAULT_WAREHOUSE || "-", SALESPERSON_NAME);

      alert("تم حفظ الطلب الجديد في ERPNext");
    } else {
      const doc = Object.assign({}, currentOrderDoc);

      doc.customer = selectedCustomerId || selectedCustomerName;
      doc.transaction_date = dateStr;
      doc.delivery_date    = dateStr;
      doc.additional_discount_percentage = disc;
      doc.ignore_pricing_rule = 1;
      doc.items = itemsPayload;

      if (DEFAULT_WAREHOUSE)  doc.set_warehouse = DEFAULT_WAREHOUSE;
      if (DEFAULT_PRICE_LIST) doc.selling_price_list = DEFAULT_PRICE_LIST;

      const resp = await erpRequest(
        "/api/resource/Sales Order/" + encodeURIComponent(currentOrderName),
        { method: "PUT", body: JSON.stringify(doc) }
      );

      const saved = resp.data || resp;
      currentOrderDoc  = saved;
      currentOrderName = saved.name;

      updateHeaderMetaUI(saved.set_warehouse || DEFAULT_WAREHOUSE || "-", SALESPERSON_NAME);

      alert("تم تحديث الطلب في ERPNext");
    }

    refreshStatusUI();
    await loadOpenOrdersFromERPNext();
    showListScreen();
  } catch (e) {
    console.error("Save error:", e);
    alert("فشل حفظ الطلب في ERPNext");
  }
}

// ============= CANCEL ORDER (DELETE draft / CANCEL submitted) =============
async function cancelOrderInERPNext() {
  if (!currentOrderName || !currentOrderDoc) {
    alert("لا توجد طلبية مفتوحة");
    return;
  }

  if (currentOrderDoc.docstatus === 0) {
    if (!confirm("سيتم حذف الطلب (مسودة). هل أنت متأكد؟")) return;
    try {
      await erpRequest(
        "/api/resource/Sales Order/" + encodeURIComponent(currentOrderName),
        { method: "DELETE" }
      );
      alert("تم حذف الطلب (مسودة)");
      currentOrderName = null;
      currentOrderDoc  = null;
      currentItems     = [];
      await loadOpenOrdersFromERPNext();
      showListScreen();
    } catch (e) {
      console.error("Delete error:", e);
      alert("فشل حذف الطلب من ERPNext");
    }
    return;
  }

  if (currentOrderDoc.docstatus === 1) {
    if (!confirm("سيتم إلغاء الطلب في ERPNext. هل أنت متأكد؟")) return;
    try {
      await erpRequest(
        "/api/resource/Sales Order/" + encodeURIComponent(currentOrderName),
        { method: "POST", body: JSON.stringify({ run_method: "cancel" }) }
      );

      const refreshed = await erpRequest(
        "/api/resource/Sales Order/" + encodeURIComponent(currentOrderName)
      );
      const doc = refreshed.data || refreshed;

      currentOrderDoc  = doc;
      currentOrderName = doc.name;
      refreshStatusUI();
      alert("تم إلغاء الطلب في ERPNext");
      await loadOpenOrdersFromERPNext();
      showListScreen();
    } catch (e) {
      console.error("Cancel error:", e);
      alert("فشل إلغاء الطلب في ERPNext");
    }
    return;
  }

  alert("لا يمكن إلغاء هذا الطلب في هذه الحالة");
}

// ============= SUBMIT ORDER =============
async function submitOrderInERPNext() {
  if (!currentOrderName || !currentOrderDoc) {
    alert("يرجى حفظ الطلب أولاً");
    return;
  }
  if (currentOrderDoc.docstatus === 1) {
    alert("الطلب معتمد مسبقاً");
    return;
  }

  if (!confirm("هل تريد اعتماد الطلب في ERPNext؟")) return;

  try {
    const docname = encodeURIComponent(currentOrderName);

    await erpRequest(
      "/api/resource/Sales Order/" + docname,
      { method: "POST", body: JSON.stringify({ run_method: "submit" }) }
    );

    const refreshed = await erpRequest("/api/resource/Sales Order/" + docname);
    const doc = refreshed.data || refreshed;

    currentOrderDoc  = doc;
    currentOrderName = doc.name;
    refreshStatusUI();
    alert("تم اعتماد الطلب في ERPNext");
    await loadOpenOrdersFromERPNext();
    showListScreen();
  } catch (e) {
    console.error("Submit error:", e);
    alert("فشل اعتماد الطلب في ERPNext");
  }
}

// ============= INIT APP =============
async function initMobileOrdersApp() {
  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("orderDate");
  if (dateInput && !dateInput.value) dateInput.value = today;

  const fab = document.querySelector(".mobile-fab");
  if (fab) fab.addEventListener("click", showOrderTypeModal);

  document.getElementById("saleBtn").addEventListener("click", () => {
    currentOrderType = "sale";
    document.getElementById("orderTypeBarText").textContent = "بيع";
    hideOrderTypeModal();

    currentOrderName = null;
    currentOrderDoc  = null;
    selectedCustomerName = "";
    selectedCustomerId   = "";
    document.getElementById("orderFormTitle").textContent = "طلبية جديدة";
    document.getElementById("invoiceNumber").value = "EA-XXXXXX";
    document.getElementById("customerInput").value = "";
    document.getElementById("discountPercent").value = "0";
    dateInput.value = today;

    currentItems = [];
    renderItemsList();
    refreshStatusUI();

    updateHeaderMetaUI(DEFAULT_WAREHOUSE || "-", SALESPERSON_NAME);
    showOrderFormScreen();
  });

  document.getElementById("returnBtn").addEventListener("click", () => {
    currentOrderType = "return";
    document.getElementById("orderTypeBarText").textContent = "ترجيع";
    hideOrderTypeModal();

    currentOrderName = null;
    currentOrderDoc  = null;
    selectedCustomerName = "";
    selectedCustomerId   = "";
    document.getElementById("orderFormTitle").textContent = "طلبية ترجيع جديدة";
    document.getElementById("invoiceNumber").value = "EA-XXXXXX";
    document.getElementById("customerInput").value = "";
    document.getElementById("discountPercent").value = "0";
    dateInput.value = today;

    currentItems = [];
    renderItemsList();
    refreshStatusUI();

    updateHeaderMetaUI(DEFAULT_WAREHOUSE || "-", SALESPERSON_NAME);
    showOrderFormScreen();
  });

  document.getElementById("cancelOrderTypeBtn").addEventListener("click", hideOrderTypeModal);

  document.getElementById("orderFormBackBtn").addEventListener("click", showListScreen);
  document.getElementById("cancelOrderBtn").addEventListener("click", showListScreen);

  document.getElementById("saveOrderBtn").addEventListener("click", saveOrderToERPNext);
  document.getElementById("cancelErpOrderBtn").addEventListener("click", cancelOrderInERPNext);
  document.getElementById("submitOrderBtn").addEventListener("click", submitOrderInERPNext);

  document.getElementById("addItemBtn").addEventListener("click", openItemModalForNew);
  document.getElementById("cancelItemBtn").addEventListener("click", hideItemModal);

  document.getElementById("saveItemBtn").addEventListener("click", () => {
    const name  = document.getElementById("itemNameInput").value.trim();
    let qty     = parseInt(document.getElementById("qtyInput").value || "1", 10);
    const mode  = getItemMode();

    if (!name) { alert("الرجاء اختيار الصنف"); return; }
    if (isNaN(qty) || qty < 1) qty = 1;

    const code = itemCodeByLabel[name] || null;

    let total = 0;
    if (mode === "free") {
      total = 0;
    } else {
      const price = code ? Number(itemPriceByCode[code] || 0) : 0;
      total = price * qty;
      if (total === 0) {
        if (!confirm("لا يوجد سعر لهذا الصنف في قائمة الأسعار. سيتم حفظه بسعر 0. هل تريد المتابعة؟")) return;
      }
    }

    const obj = { name, code, qty, total, is_free: (mode === "free") };

    if (editingItemIndex == null) currentItems.push(obj);
    else currentItems[editingItemIndex] = obj;

    hideItemModal();
    renderItemsList();
  });

  document.getElementById("qtyMinusBtn").addEventListener("click", () => {
    const input = document.getElementById("qtyInput");
    let val = parseInt(input.value || "1", 10);
    if (isNaN(val) || val <= 1) val = 1; else val -= 1;
    input.value = val;
    recalcModalTotal();
  });
  document.getElementById("qtyPlusBtn").addEventListener("click", () => {
    const input = document.getElementById("qtyInput");
    let val = parseInt(input.value || "1", 10);
    if (isNaN(val) || val < 1) val = 1; else val += 1;
    input.value = val;
    recalcModalTotal();
  });

  document.getElementById("discountMinusBtn").addEventListener("click", () => {
    const input = document.getElementById("discountPercent");
    let val = parseFloat(input.value || "0");
    if (isNaN(val)) val = 0;
    val = Math.max(0, val - 0.5);
    input.value = val.toFixed(1);
  });
  document.getElementById("discountPlusBtn").addEventListener("click", () => {
    const input = document.getElementById("discountPercent");
    let val = parseFloat(input.value || "0");
    if (isNaN(val)) val = 0;
    val = Math.min(100, val + 0.5);
    input.value = val.toFixed(1);
  });

  document.getElementById("saleToggleBtn").addEventListener("click", () => setItemMode("sale"));
  document.getElementById("freeToggleBtn").addEventListener("click", () => setItemMode("free"));

  document.getElementById("itemNameInput").addEventListener("click", showItemListModal);
  document.getElementById("itemSearchInput").addEventListener("input", function () {
    filterAndRenderItemList(this.value);
  });
  document.getElementById("itemListDoneBtn").addEventListener("click", hideItemListModal);

  document.getElementById("customerInput").addEventListener("click", showCustomerListModal);
  document.getElementById("customerSearchInput").addEventListener("input", function () {
    filterAndRenderCustomerList(this.value);
  });
  document.getElementById("customerListDoneBtn").addEventListener("click", hideCustomerListModal);

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
