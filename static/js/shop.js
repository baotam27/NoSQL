let activeCategory = "Tất cả";
let scenarioRunning = false;
const cartsByUser = {
  usr_1001: [],
  usr_2049: [],
  usr_3088: [],
};
const sessionsByUser = {
  usr_1001: "sess_1001_" + Math.floor(Date.now() / 1000),
  usr_2049: "sess_2049_" + Math.floor(Date.now() / 1000),
  usr_3088: "sess_3088_" + Math.floor(Date.now() / 1000),
};

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatVnd(amount) {
  return Number(amount || 0).toLocaleString("vi-VN") + " VNĐ";
}

function showToast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

function showError(msg) {
  const banner = document.getElementById("errorBanner");
  if (!banner) return;
  if (!msg) {
    banner.style.display = "none";
    banner.textContent = "";
    return;
  }
  banner.style.display = "block";
  banner.innerHTML = "<strong>Lỗi Bigtable:</strong> " + escapeHtml(msg);
}

function animatePipeline() {
  const bar = document.getElementById("pipelineBar");
  const nodes = ["pipeNode1", "pipeNode2", "pipeNode3", "pipeNode4"].map((id) =>
    document.getElementById(id)
  );
  if (!bar) return;
  bar.classList.add("active-flow");
  nodes.forEach((n, idx) => {
    if (!n) return;
    setTimeout(() => n.classList.add("lit"), idx * 110);
    setTimeout(() => n.classList.remove("lit"), 950 + idx * 90);
  });
  setTimeout(() => bar.classList.remove("active-flow"), 1300);
}

function renderRowKeyAnatomy(parts) {
  const container = document.getElementById("rkAnatomy");
  if (!container || !parts || !parts.user_id) return;
  container.innerHTML = `
    <span class="rk-part rk-salt">Salt đảo ngược: ${escapeHtml(parts.reversed_uid)}</span>
    <span class="rk-part rk-uid">User ID: ${escapeHtml(parts.user_id)}</span>
    <span class="rk-part rk-ts">Reverse TS: ${escapeHtml(parts.reverse_ts)}</span>
  `;
}

function flashRowKeyBox() {
  const box = document.getElementById("latestRowKeyBox");
  if (!box) return;
  box.classList.remove("flash");
  void box.offsetWidth;
  box.classList.add("flash");
}

function getFilterParams() {
  const rangeEl = document.getElementById("rangeFilter");
  const eventEl = document.getElementById("eventTypeFilter");
  const familyEl = document.getElementById("familyFilter");
  return {
    range_minutes: rangeEl ? rangeEl.value : "all",
    event_type: eventEl ? eventEl.value : "",
    families: familyEl ? familyEl.value : "",
  };
}

function applyProductFilter() {
  const keyword = document.getElementById("searchInput").value.trim().toLowerCase();
  document.querySelectorAll("#productGrid .product-card").forEach((card) => {
    const cat = card.dataset.category;
    const name = card.dataset.name;
    const specs = card.dataset.specs;
    const matchCat = activeCategory === "Tất cả" || cat === activeCategory;
    const matchKeyword =
      !keyword || name.includes(keyword) || specs.includes(keyword) || cat.toLowerCase().includes(keyword);
    card.style.display = matchCat && matchKeyword ? "flex" : "none";
  });
}

function filterCategory(category, btnEl) {
  activeCategory = category;
  document.querySelectorAll(".cat-pill").forEach((b) => {
    b.classList.toggle("active", b.dataset.cat === category || b === btnEl);
  });
  applyProductFilter();
}

function resetFilter() {
  document.getElementById("searchInput").value = "";
  activeCategory = "Tất cả";
  document.querySelectorAll(".cat-pill").forEach((b, idx) => b.classList.toggle("active", idx === 0));
  applyProductFilter();
}

function renderCart() {
  const userId = window.SHOP_STATE.currentUser;
  const cart = cartsByUser[userId] || [];
  const totalCount = cart.reduce((acc, item) => acc + (item.qty || 1), 0);
  const totalAmount = cart.reduce((acc, item) => acc + Number(item.price || 0) * (item.qty || 1), 0);

  document.getElementById("cartUserLabel").textContent = userId;
  document.getElementById("cartCount").textContent = totalCount;
  document.getElementById("cartTotal").textContent = formatVnd(totalAmount);

  const container = document.getElementById("cartItems");
  if (cart.length === 0) {
    container.innerHTML = '<span style="color: var(--muted);">Chưa có sản phẩm trong giỏ hàng.</span>';
    return;
  }

  container.innerHTML = cart
    .map(
      (item, idx) => `
      <div class="cart-item-row">
        <div>
          <strong>${escapeHtml(item.product_name)}</strong>
          <span style="color:var(--muted); font-size:0.76rem;">(${escapeHtml(item.category)})</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <button type="button" class="qty-btn" onclick="changeCartQty(${idx}, -1)">-</button>
          <strong>${item.qty || 1}</strong>
          <button type="button" class="qty-btn" onclick="changeCartQty(${idx}, 1)">+</button>
          <span style="min-width:110px; text-align:right; font-weight:600;">${formatVnd(item.price * (item.qty || 1))}</span>
        </div>
      </div>`
    )
    .join("");
}

function changeCartQty(index, delta) {
  const userId = window.SHOP_STATE.currentUser;
  const cart = cartsByUser[userId] || [];
  if (!cart[index]) return;
  cart[index].qty = (cart[index].qty || 1) + delta;
  if (cart[index].qty <= 0) {
    cart.splice(index, 1);
  }
  renderCart();
}

function renderDashboard(data, isWriteEvent = false) {
  showError("");
  const recent = data.recent || {};
  const recs = data.recommendations || {};
  const profile = data.user_profile || (window.SHOP_STATE.userProfiles || {})[window.SHOP_STATE.currentUser] || {};

  if (profile.name) {
    document.getElementById("personaAvatar").textContent = profile.avatar || "KH";
    document.getElementById("personaName").textContent = profile.name;
    document.getElementById("personaUid").textContent = `(${profile.user_id || window.SHOP_STATE.currentUser})`;
    document.getElementById("personaSegment").textContent = profile.segment || "";
  }

  const banner = recs.dynamic_banner;
  if (banner) {
    const heroEl = document.getElementById("heroBanner");
    heroEl.className = `hero-banner ${banner.theme || "theme-default"}`;
    document.getElementById("heroTag").textContent = banner.tag || "";
    document.getElementById("heroTitle").textContent = banner.title || "";
    document.getElementById("heroSubtitle").textContent = banner.subtitle || "";
  }

  const scorePillsEl = document.getElementById("scorePills");
  const scoresEntries = Object.entries(recs.category_scores || {}).sort((a, b) => b[1] - a[1]);
  if (scoresEntries.length > 0) {
    scorePillsEl.innerHTML = scoresEntries
      .map(
        ([cat, sc], idx) =>
          `<span class="score-pill ${idx === 0 ? "top" : ""}">${escapeHtml(cat)}: ${sc}đ</span>`
      )
      .join("");
  } else {
    scorePillsEl.innerHTML = '<span class="score-pill">Chưa có điểm hành vi</span>';
  }

  const rvEl = document.getElementById("recentlyViewedList");
  const rvList = recs.recently_viewed || [];
  document.getElementById("analyzedCountLabel").textContent =
    `${recs.analyzed_events_count ?? 0} sự kiện gần nhất`;
  if (rvList.length > 0) {
    rvEl.innerHTML = rvList
      .map(
        (rp) => `
        <span class="recent-chip" onclick="viewProduct('${escapeHtml(rp.product_id)}')">
          <strong>${escapeHtml(rp.product_name)}</strong>
          <span style="color:var(--danger);">${formatVnd(rp.price)}</span>
        </span>`
      )
      .join("");
  } else {
    rvEl.innerHTML = '<span style="font-size:0.78rem; color:var(--muted);">Chưa có sản phẩm vừa xem.</span>';
  }

  document.getElementById("metricPrefix").textContent = recent.prefix || "";
  document.getElementById("metricReadLatency").textContent = (recent.latency_ms ?? 0) + " ms";
  document.getElementById("scanMetaInfo").textContent =
    `${recent.scan_mode || ""} | Bộ lọc: ${recent.filter_applied || ""}`;

  const fraud = data.fraud_status;
  if (fraud) {
    const fraudBox = document.getElementById("fraudBox");
    if (fraudBox) {
      fraudBox.className = `fraud-box fraud-${fraud.risk_level || "NORMAL"}`;
      document.getElementById("fraudMessage").textContent = fraud.message || "";
      document.getElementById("fraudBadge").textContent = fraud.label || "An toàn";
      document.getElementById("fraudLatency").textContent = `Scan: ${fraud.latency_ms ?? 0} ms`;
    }
  }

  if (data.logged_event) {
    document.getElementById("metricWriteLatency").textContent = data.logged_event.write_latency_ms + " ms";
    document.getElementById("latestRowKey").textContent = data.logged_event.row_key;
    renderRowKeyAnatomy(data.logged_event.row_key_parts);
    flashRowKeyBox();
  } else if (recent.events && recent.events.length > 0) {
    document.getElementById("latestRowKey").textContent = recent.events[0].row_key;
    renderRowKeyAnatomy(recent.events[0].row_key_parts);
  } else {
    document.getElementById("latestRowKey").textContent = "Không có Row Key khớp bộ lọc hiện tại";
    document.getElementById("rkAnatomy").innerHTML = "";
  }

  const tbody = document.getElementById("clickstreamBody");
  const events = recent.events || [];
  if (events.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; color: var(--muted); padding: 20px;">
          Không có sự kiện nào phù hợp với điều kiện lọc.
        </td>
      </tr>`;
  } else {
    tbody.innerHTML = events
      .map((ev, idx) => {
        const ce = ev.cf_event || {};
        const cp = ev.cf_product || {};
        const cd = ev.cf_device || {};
        const evType = escapeHtml(ce.event_type || "");
        const eventCell = ce.event_type
          ? `<span class="ev-badge ev-${evType}">${evType}</span>
             <div>session: <span class="mono">${escapeHtml(ce.session_id)}</span></div>
             <div>url: <span class="mono">${escapeHtml(ce.page_url)}</span></div>`
          : '<span style="color:var(--muted);">Đã ẩn bởi FamilyFilter</span>';

        const productHtml = cp.product_name
          ? `<div><strong>${escapeHtml(cp.product_name)}</strong> (${escapeHtml(cp.product_id)})</div>
             <div>Danh mục: ${escapeHtml(cp.category)}</div>
             <div>Giá: ${escapeHtml(cp.price)}</div>`
          : "";
        const kwHtml = cp.search_keyword
          ? `<div>Từ khóa: <strong>${escapeHtml(cp.search_keyword)}</strong></div>`
          : "";
        const productCell = productHtml || kwHtml || '<span style="color:var(--muted);">-</span>';

        const deviceCell = cd.device_type
          ? `<div>${escapeHtml(cd.device_type)}</div>
             <div>OS: ${escapeHtml(cd.os)}</div>
             <div>Vùng: ${escapeHtml(cd.ip_region)}</div>`
          : '<span style="color:var(--muted);">Đã ẩn bởi FamilyFilter</span>';

        const rowClass = isWriteEvent && idx === 0 ? 'class="new-row-anim"' : "";
        return `
          <tr ${rowClass}>
            <td>
              <div><strong>${escapeHtml(ev.time_display)}</strong></div>
              <div class="mono" style="color: #0369a1;">${escapeHtml(ev.row_key)}</div>
            </td>
            <td>${eventCell}</td>
            <td>${productCell}</td>
            <td>${deviceCell}</td>
          </tr>`;
      })
      .join("");
  }

  document.getElementById("recCategoryBadge").textContent = recs.target_category || "Nổi bật";
  document.getElementById("recReason").textContent = recs.reason || "";
  const recItems = recs.recommendations || [];
  document.getElementById("recGrid").innerHTML = recItems
    .map(
      (rp) => `
      <div class="rec-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="cat-tag">${escapeHtml(rp.category)}</span>
          <strong style="color: var(--danger); font-size:0.86rem;">${formatVnd(rp.price)}</strong>
        </div>
        <strong style="font-size:0.88rem;">${escapeHtml(rp.product_name)}</strong>
        <div style="display:flex; gap:6px;">
          <button type="button" class="btn btn-outline" style="flex:1; padding:6px 8px; font-size:0.78rem;" onclick="viewProduct('${escapeHtml(rp.product_id)}')">Xem</button>
          <button type="button" class="btn btn-primary" style="flex:1; padding:6px 8px; font-size:0.78rem;" onclick="addToCart('${escapeHtml(rp.product_id)}')">Thêm giỏ</button>
        </div>
      </div>`
    )
    .join("");
}

async function sendEvent(payload) {
  animatePipeline();
  const userId = window.SHOP_STATE.currentUser;
  const region = document.getElementById("regionSelect").value;
  const filters = getFilterParams();
  const body = {
    user_id: userId,
    session_id: sessionsByUser[userId],
    ip_region: region,
    range_minutes: filters.range_minutes,
    filter_event_type: filters.event_type,
    families: filters.families,
    ...payload,
  };
  const res = await fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok || data.status !== "ok") {
    showError(data.message || "Không thể ghi sự kiện vào Bigtable");
    return null;
  }
  renderDashboard(data, true);
  return data;
}

async function refreshClickstream() {
  const userId = window.SHOP_STATE.currentUser;
  const filters = getFilterParams();
  const qs = new URLSearchParams({
    user_id: userId,
    limit: "10",
    range_minutes: filters.range_minutes,
    event_type: filters.event_type,
    families: filters.families,
  });
  const res = await fetch(`/api/clickstream?${qs.toString()}`);
  const data = await res.json();
  if (!res.ok || data.status !== "ok") {
    showError(data.message || "Không thể đọc dữ liệu từ Bigtable");
    return;
  }
  renderDashboard(data, false);
}

async function switchUser(userId) {
  window.SHOP_STATE.currentUser = userId;
  const profile = (window.SHOP_STATE.userProfiles || {})[userId];
  if (profile && profile.default_region) {
    document.getElementById("regionSelect").value = profile.default_region;
  }
  document.querySelectorAll(".user-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.user === userId);
  });
  renderCart();
  await refreshClickstream();
  showToast(`Đã chuyển sang hồ sơ ${profile ? profile.name : userId} (${userId})`);
}

async function handleSearch(e) {
  if (e) e.preventDefault();
  applyProductFilter();
  const keyword = document.getElementById("searchInput").value.trim();
  if (!keyword) return;
  const result = await sendEvent({
    event_type: "search_keyword",
    search_keyword: keyword,
    page_url: `/search?q=${encodeURIComponent(keyword)}`,
  });
  if (result) showToast(`Đã ghi search_keyword: "${keyword}"`);
}

async function quickSearch(keyword) {
  document.getElementById("searchInput").value = keyword;
  await handleSearch(null);
}

async function viewProduct(productId) {
  const p = window.SHOP_STATE.productMap[productId];
  if (!p) return;

  document.getElementById("modalCategory").textContent = p.category;
  document.getElementById("modalTitle").textContent = p.product_name;
  document.getElementById("modalRating").textContent = `★ ${p.rating} (${p.reviews_count} đánh giá) • Giảm ${p.discount_pct}%`;
  document.getElementById("modalSpecs").textContent = p.specs;
  document.getElementById("modalDesc").textContent = p.description;
  document.getElementById("modalPrice").textContent = formatVnd(p.price);
  document.getElementById("modalAddBtn").onclick = () => {
    closeModal();
    addToCart(p.product_id);
  };
  document.getElementById("modalBuyBtn").onclick = () => {
    closeModal();
    buyNow(p.product_id);
  };
  document.getElementById("detailModal").classList.add("open");

  const result = await sendEvent({
    event_type: "view_product",
    product_id: p.product_id,
    page_url: `/products/${p.product_id}`,
  });
  if (result) showToast(`Đã ghi view_product: ${p.product_name}`);
}

function closeModal() {
  document.getElementById("detailModal").classList.remove("open");
}

function closeReceiptModal() {
  document.getElementById("receiptModal").classList.remove("open");
}

function showOrderReceipt(summaryText, totalAmount, loggedEvent) {
  document.getElementById("receiptSummary").textContent = summaryText;
  document.getElementById("receiptTotal").textContent = formatVnd(totalAmount);
  document.getElementById("receiptRowKey").textContent = loggedEvent.row_key;
  document.getElementById("receiptLatency").textContent =
    `Độ trễ ghi Bigtable: ${loggedEvent.write_latency_ms} ms | Session: ${loggedEvent.cf_event.session_id}`;
  document.getElementById("receiptModal").classList.add("open");
}

async function addToCart(productId) {
  const p = window.SHOP_STATE.productMap[productId];
  if (!p) return;
  const userId = window.SHOP_STATE.currentUser;
  cartsByUser[userId] = cartsByUser[userId] || [];
  const existing = cartsByUser[userId].find((i) => i.product_id === productId);
  if (existing) {
    existing.qty = (existing.qty || 1) + 1;
  } else {
    cartsByUser[userId].push({ ...p, qty: 1 });
  }
  renderCart();

  const result = await sendEvent({
    event_type: "add_to_cart",
    product_id: p.product_id,
    page_url: `/cart/add/${p.product_id}`,
  });
  if (result) showToast(`Đã thêm vào giỏ và ghi Bigtable: ${p.product_name}`);
}

async function buyNow(productId) {
  const p = window.SHOP_STATE.productMap[productId];
  if (!p) return;
  const result = await sendEvent({
    event_type: "purchase_success",
    product_id: p.product_id,
    product_name: p.product_name,
    category: p.category,
    price: p.price,
    search_keyword: p.product_name,
    page_url: `/checkout/buy-now/${p.product_id}`,
  });
  if (result && result.logged_event) {
    showOrderReceipt(`Mua nhanh 1x ${p.product_name} (${p.category})`, p.price, result.logged_event);
  }
}

async function checkoutCart() {
  const userId = window.SHOP_STATE.currentUser;
  const cart = cartsByUser[userId] || [];
  if (cart.length === 0) {
    showToast("Giỏ hàng đang trống, hãy thêm sản phẩm trước khi thanh toán.");
    return;
  }
  const primary = cart[cart.length - 1];
  const totalCount = cart.reduce((acc, item) => acc + (item.qty || 1), 0);
  const totalAmount = cart.reduce((acc, item) => acc + Number(item.price || 0) * (item.qty || 1), 0);
  const summaryNames = cart.map((i) => `${i.qty || 1}x ${i.product_name}`).join(", ");

  const result = await sendEvent({
    event_type: "purchase_success",
    product_id: primary.product_id,
    product_name: totalCount > 1 ? `${primary.product_name} (+${totalCount - 1} SP)` : primary.product_name,
    category: primary.category,
    price: totalAmount,
    search_keyword: summaryNames,
    page_url: "/checkout/success",
  });

  if (result && result.logged_event) {
    cartsByUser[userId] = [];
    renderCart();
    showOrderReceipt(summaryNames, totalAmount, result.logged_event);
  }
}

async function runDemoScenario(scenarioName) {
  if (scenarioRunning) {
    showToast("Đang chạy một kịch bản mẫu, vui lòng đợi hoàn tất.");
    return;
  }
  const scenarios = {
    laptop: [
      { event_type: "search_keyword", search_keyword: "MacBook", page_url: "/search?q=MacBook" },
      { event_type: "view_product", product_id: "SP001", page_url: "/products/SP001" },
      { event_type: "add_to_cart", product_id: "SP001", page_url: "/cart/add/SP001" },
    ],
    audio: [
      { event_type: "search_keyword", search_keyword: "Sony", page_url: "/search?q=Sony" },
      { event_type: "view_product", product_id: "SP007", page_url: "/products/SP007" },
      { event_type: "add_to_cart", product_id: "SP008", page_url: "/cart/add/SP008" },
    ],
    phone: [
      { event_type: "view_product", product_id: "SP003", page_url: "/products/SP003" },
      { event_type: "add_to_cart", product_id: "SP003", page_url: "/cart/add/SP003" },
      {
        event_type: "purchase_success",
        product_id: "SP003",
        product_name: "iPhone 16 Pro Max 256GB",
        category: "Điện thoại",
        price: 33990000,
        page_url: "/checkout/success",
      },
    ],
    bot: [
      { event_type: "search_keyword", search_keyword: "iPhone", page_url: "/search?q=iPhone" },
      { event_type: "view_product", product_id: "SP003", page_url: "/products/SP003" },
      { event_type: "view_product", product_id: "SP004", page_url: "/products/SP004" },
      { event_type: "add_to_cart", product_id: "SP003", page_url: "/cart/add/SP003" },
      { event_type: "view_product", product_id: "SP001", page_url: "/products/SP001" },
      { event_type: "add_to_cart", product_id: "SP001", page_url: "/cart/add/SP001" },
      { event_type: "view_product", product_id: "SP007", page_url: "/products/SP007" },
      { event_type: "add_to_cart", product_id: "SP007", page_url: "/cart/add/SP007" },
      { event_type: "search_keyword", search_keyword: "Voucher", page_url: "/search?q=Voucher" },
    ],
  };

  const steps = scenarios[scenarioName] || scenarios.laptop;
  const delayMs = scenarioName === "bot" ? 120 : 420;
  scenarioRunning = true;
  showToast(
    scenarioName === "bot"
      ? "Đang mô phỏng Bot gửi 9 yêu cầu liên tiếp trong 10 giây..."
      : "Đang chạy chuỗi hành vi tự động lên Bigtable..."
  );
  try {
    for (const step of steps) {
      await sendEvent(step);
      await new Promise((r) => setTimeout(r, delayMs));
    }
    showToast(
      scenarioName === "bot"
        ? "Đã kích hoạt cảnh báo Fraud Detection từ Bigtable Time-Range Scan"
        : "Đã hoàn tất kịch bản mẫu và cập nhật giao diện cá nhân hóa"
    );
  } finally {
    scenarioRunning = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.SHOP_STATE) {
    renderCart();
  }
});
