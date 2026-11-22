let simPollTimer = null;

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

function renderBars(containerId, countsObj, color) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const entries = Object.entries(countsObj || {});
  if (entries.length === 0) {
    el.innerHTML = '<div style="color:var(--muted); font-size:0.84rem;">Chưa có dữ liệu.</div>';
    return;
  }
  const maxVal = Math.max(...entries.map((e) => e[1]), 1);
  el.innerHTML = entries
    .map(([label, val]) => {
      const pct = Math.round((val / maxVal) * 100);
      return `
        <div class="bar-row">
          <span class="bar-label">${escapeHtml(label)}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:${pct}%; background:${color};"></div>
          </div>
          <span class="bar-val">${val}</span>
        </div>`;
    })
    .join("");
}

function renderAnalyticsData(data) {
  const ov = data.overview || {};
  const dm = data.daily_metrics || {};
  const funnel = ov.funnel || {};

  document.getElementById("kpiSampled").textContent = ov.sampled_rows ?? 0;
  document.getElementById("kpiUsers").textContent = ov.unique_users ?? 0;
  document.getElementById("kpiCartRate").textContent = (funnel.cart_rate_pct ?? 0) + "%";
  document.getElementById("kpiPurchaseRate").textContent = (funnel.purchase_rate_pct ?? 0) + "%";
  document.getElementById("overviewLatency").textContent = (ov.read_latency_ms ?? 0) + " ms";
  document.getElementById("metricsLatency").textContent = (dm.latency_ms ?? 0) + " ms";

  renderBars(
    "funnelBars",
    {
      "Tìm kiếm": funnel.search_keyword || 0,
      "Xem SP": funnel.view_product || 0,
      "Thêm giỏ": funnel.add_to_cart || 0,
      "Mua hàng": funnel.purchase_success || 0,
    },
    "#2563eb"
  );
  renderBars("tabletBars", ov.tablet_distribution || {}, "#0284c7");
  renderBars("deviceBars", ov.devices || {}, "#059669");
  renderBars("regionBars", ov.regions || {}, "#7c3aed");

  const kwBox = document.getElementById("keywordList");
  const kws = ov.top_keywords || [];
  kwBox.innerHTML = kws.length
    ? kws.map((k) => `<span class="cat-tag" style="margin-right:6px;">${escapeHtml(k.keyword)} (${k.count})</span>`).join("")
    : '<span style="color:var(--muted); font-size:0.84rem;">Chưa có từ khóa tìm kiếm.</span>';

  const tbody = document.getElementById("productMetricsBody");
  if (!dm.available) {
    tbody.innerHTML =
      '<tr><td colspan="6" style="text-align:center; color:var(--muted); padding:16px;">Bảng product_metrics chưa được tạo trên cụm hiện tại.</td></tr>';
    return;
  }
  const products = dm.products || [];
  tbody.innerHTML = products
    .map(
      (p) => `
      <tr>
        <td><strong>${escapeHtml(p.product_name)}</strong><div class="mono">${escapeHtml(p.product_id)} (${escapeHtml(p.category)})</div></td>
        <td>${p.views}</td>
        <td>${p.carts}</td>
        <td>${p.purchases}</td>
        <td>${formatVnd(p.revenue)}</td>
        <td><strong>${p.conversion_pct}%</strong></td>
      </tr>`
    )
    .join("");
}

async function refreshAnalytics() {
  const res = await fetch("/api/analytics/summary");
  const data = await res.json();
  if (res.ok && data.status === "ok") {
    renderAnalyticsData(data);
  }
}

async function runScanBenchmark() {
  const userId = document.getElementById("benchUserSelect").value;
  const outEl = document.getElementById("scanBenchResult");
  outEl.textContent = "Đang đo tốc độ truy vấn...";
  const res = await fetch("/api/analytics/scan-benchmark", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  const data = await res.json();
  if (!res.ok || data.status !== "ok") {
    outEl.textContent = "Lỗi: " + (data.message || "Không thể đo");
    return;
  }
  const b = data.benchmark;
  outEl.innerHTML = `
    <div><strong>Prefix Scan (${escapeHtml(b.prefix)}*):</strong> ${b.prefix_scan_ms} ms (${b.prefix_rows} dòng trả về)</div>
    <div><strong>Full Table Scan (${b.total_scanned_rows} dòng):</strong> ${b.full_scan_ms} ms</div>
    <div style="color:#047857; font-weight:700; margin-top:4px;">Prefix Scan nhanh hơn ${b.speedup} lần</div>
  `;
}

function copySqlText(btnEl) {
  const pre = btnEl.closest(".sql-card").querySelector("pre");
  if (!pre) return;
  navigator.clipboard.writeText(pre.textContent || "");
  const oldText = btnEl.textContent;
  btnEl.textContent = "Đã sao chép";
  setTimeout(() => {
    btnEl.textContent = oldText;
  }, 1600);
}

function updateSimulatorUI(sim) {
  const statusEl = document.getElementById("simStatusBadge");
  const startBtn = document.getElementById("simStartBtn");
  const stopBtn = document.getElementById("simStopBtn");
  document.getElementById("simCount").textContent = sim.generated_count ?? 0;
  document.getElementById("simLastKey").textContent = sim.last_row_key || "Chưa có";

  if (sim.running) {
    statusEl.textContent = `Đang chạy (${sim.rate_per_sec} sự kiện/giây)`;
    statusEl.className = "ev-badge ev-purchase_success";
    startBtn.disabled = true;
    stopBtn.disabled = false;
    if (!simPollTimer) {
      simPollTimer = setInterval(async () => {
        await pollSimulatorStatus();
        await refreshAnalytics();
      }, 2500);
    }
  } else {
    statusEl.textContent = "Đang dừng";
    statusEl.className = "ev-badge ev-search_keyword";
    startBtn.disabled = false;
    stopBtn.disabled = true;
    if (simPollTimer) {
      clearInterval(simPollTimer);
      simPollTimer = null;
    }
  }
}

async function pollSimulatorStatus() {
  const res = await fetch("/api/simulator/status");
  const data = await res.json();
  if (res.ok && data.status === "ok") {
    updateSimulatorUI(data.simulator);
  }
}

async function startSimulator() {
  const rate = Number(document.getElementById("simRateInput").value || 5);
  const res = await fetch("/api/simulator/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rate_per_sec: rate }),
  });
  const data = await res.json();
  if (res.ok && data.status === "ok") {
    updateSimulatorUI(data.simulator);
  }
}

async function stopSimulator() {
  const res = await fetch("/api/simulator/stop", { method: "POST" });
  const data = await res.json();
  if (res.ok && data.status === "ok") {
    updateSimulatorUI(data.simulator);
    await refreshAnalytics();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.ANALYTICS_INIT) {
    renderAnalyticsData(window.ANALYTICS_INIT);
    pollSimulatorStatus();
  }
});
