const API_BASE = "http://127.0.0.1:8000";

const els = {
  priority: document.getElementById("priority"),
  status: document.getElementById("status"),
  explainMode: document.getElementById("explainMode"),
  explainModeEst: document.getElementById("explainModeEst"),
  explainModeCompare: document.getElementById("explainModeCompare"),
  customFee: document.getElementById("customFee"),
  estimateStatus: document.getElementById("estimateStatus"),
  singleResult: document.getElementById("singleResult"),
  estimateResult: document.getElementById("estimateResult"),
  compareResult: document.getElementById("compareResult"),
  compareGrid: document.getElementById("compareGrid"),
  compareSummary: document.getElementById("compareSummary"),
  compareVerdict: document.getElementById("compareVerdict"),
  compareStatus: document.getElementById("compareStatus"),
  liveUpdated: document.getElementById("liveUpdated"),
  liveMempool: document.getElementById("liveMempool"),
  liveFast: document.getElementById("liveFast"),
  liveNormal: document.getElementById("liveNormal"),
  liveCache: document.getElementById("liveCache"),
  liveError: document.getElementById("liveError"),
  liveState: document.getElementById("liveState"),
  liveNote: document.getElementById("liveNote"),
  minerStatus: document.getElementById("minerStatus"),
  minerEval: document.getElementById("minerEval"),
  minerTargetsGrid: document.getElementById("minerTargetsGrid"),
  btnMinerRefresh: document.getElementById("btnMinerRefresh"),
  minerCount: document.getElementById("minerCount"),
  minerFee: document.getElementById("minerFee"),
  targetBlocks: document.getElementById("targetBlocks"),
  minerTargetSummary: document.getElementById("minerTargetSummary"),
  btnRecommend: document.getElementById("btnRecommend"),
  btnCompare: document.getElementById("btnCompare"),
  btnEstimate: document.getElementById("btnEstimate"),
  tabs: document.querySelectorAll(".tab"),
  tabPanels: document.querySelectorAll(".tab-panel"),
  historyList: document.getElementById("historyList"),
  btnHistory: document.getElementById("btnHistory"),
  historyInsight: document.getElementById("historyInsight"),
};

function setStatus(message, isError = false) {
  els.status.textContent = message;
  els.status.classList.toggle("error", isError);
}

function setCompareStatus(message, isError = false) {
  if (!els.compareStatus) return;
  els.compareStatus.textContent = message;
  els.compareStatus.classList.toggle("error", isError);
  els.compareStatus.classList.toggle("hidden", !message);
}

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

function buildList(items, className = "explanation") {
  const list = document.createElement("ul");
  list.className = className;
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  return list;
}

function buildBadge(text, extraClass = "") {
  const span = document.createElement("span");
  span.className = `badge badge-${text} ${extraClass}`.trim();
  span.textContent = text;
  return span;
}

function renderRecommendation(target, title, rec) {
  target.innerHTML = "";
  target.classList.remove("hidden");

  const heading = document.createElement("div");
  heading.className = "result-header";
  const h2 = document.createElement("h2");
  h2.textContent = title;
  heading.appendChild(h2);
  heading.appendChild(buildBadge(rec.confidence));
  const risk = buildBadge(rec.risk_level, `badge-risk-${rec.risk_level}`);
  heading.appendChild(risk);
  if (rec.cache_used) {
    heading.appendChild(buildBadge("cache"));
  }

  const stats = document.createElement("div");
  stats.className = "stats";
  stats.innerHTML = `
    <div><span>Fee</span><b>${rec.recommended_fee_sat_vb} sat/vB</b></div>
    <div><span>Base fee</span><b>${rec.base_fee_sat_vb} sat/vB</b></div>
    <div><span>Mode</span><b>${rec.mode}</b></div>
    ${rec.input_fee_sat_vb ? `<div><span>Input fee</span><b>${rec.input_fee_sat_vb} sat/vB</b></div>` : ""}
    <div><span>Blocks</span><b>${rec.eta_blocks_min}-${rec.eta_blocks_max}</b></div>
    <div><span>ETA</span><b>${rec.eta_minutes_min}-${rec.eta_minutes_max} min</b></div>
    <div><span>Mempool tx</span><b>${rec.mempool_tx_count.toLocaleString()}</b></div>
  `;

  const explanationBlock = document.createElement("div");
  explanationBlock.className = "details";
  const label = document.createElement("p");
  label.className = "muted";
  label.textContent = "Why this fee";
  explanationBlock.appendChild(label);
  explanationBlock.appendChild(buildList(rec.explanation));

  if (rec.agent_summary) {
    const summaryBlock = document.createElement("div");
    summaryBlock.className = "status";
    summaryBlock.textContent = rec.agent_summary;
    target.appendChild(summaryBlock);
  }

  if (rec.what_if_hint) {
    const hintBlock = document.createElement("div");
    hintBlock.className = "status";
    hintBlock.textContent = rec.what_if_hint;
    target.appendChild(hintBlock);
  }

  if (rec.llm_explanation) {
    const llmBlock = document.createElement("div");
    llmBlock.className = "details";
    const llmLabel = document.createElement("p");
    llmLabel.className = "muted";
    llmLabel.textContent = "LLM Explanation";
    const llmText = document.createElement("p");
    llmText.textContent = rec.llm_explanation;
    llmBlock.appendChild(llmLabel);
    llmBlock.appendChild(llmText);
    target.appendChild(llmBlock);
  }

  const rulesBlock = document.createElement("div");
  rulesBlock.className = "details";
  const rulesLabel = document.createElement("p");
  rulesLabel.className = "muted";
  rulesLabel.textContent = "Rules fired";
  rulesBlock.appendChild(rulesLabel);
  rulesBlock.appendChild(buildList(rec.rules_fired || [], "rules"));

  target.appendChild(heading);
  target.appendChild(stats);
  target.appendChild(explanationBlock);
  target.appendChild(rulesBlock);
}

async function handleRecommend() {
  const priority = els.priority.value;
  const explain = els.explainMode.value;
  setStatus("Loading recommendation...");
  els.singleResult.classList.add("hidden");
  els.estimateResult.classList.add("hidden");
  
  // Düzeltme: compareResult'ı gizleyen kod kaldırıldı.

  try {
    const explainParam = explain ? `&explain=${explain}` : "";
    const data = await fetchJson(`/recommend?priority=${priority}${explainParam}`);
    renderRecommendation(els.singleResult, `${priority} priority`, data);
    setStatus("Done");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function handleCompare() {
  setCompareStatus("Loading comparison...");
  els.singleResult.classList.add("hidden");
  els.estimateResult.classList.add("hidden");
  
  // Düzeltme: compareResult'ı (butonları) gizleyen kod kaldırıldı.
  
  els.compareSummary.classList.add("hidden");
  els.compareVerdict.classList.add("hidden");
  
  // Grid temizleniyor ama ana kart gizlenmiyor
  els.compareGrid.innerHTML = "";

  try {
    const explain = els.explainModeCompare.value;
    const explainParam = explain ? `?explain=${explain}` : "";
    const data = await fetchJson(`/compare${explainParam}`);
    renderCompareVerdict(data.verdict_title, data.verdict_text);
    renderCompareSummary(
      data.overpay_percent_fast_vs_medium,
      data.overpay_delta_fast_vs_medium_sat_vb,
      data.note
    );
    renderRecommendation(appendCompareCard("fast"), "Fast", data.fast);
    renderRecommendation(appendCompareCard("medium"), "Medium", data.medium);
    renderRecommendation(appendCompareCard("slow"), "Slow", data.slow);
    
    // İşlem bitince emin olmak için tekrar görünür yapıyoruz (gerekli değil ama güvenli)
    els.compareResult.classList.remove("hidden");
    setCompareStatus("Done");
  } catch (err) {
    setCompareStatus(err.message, true);
  }
}

function appendCompareCard() {
  const card = document.createElement("div");
  card.className = "compare-card";
  els.compareGrid.appendChild(card);
  return card;
}

function renderCompareSummary(overpayPercent, deltaSatVb, note) {
  const rounded = Math.round(overpayPercent * 10) / 10;
  els.compareSummary.textContent = `Fast vs Medium overpay: ${rounded}% (${deltaSatVb} sat/vB). ${note || ""}`;
  els.compareSummary.classList.remove("hidden");
}

function renderCompareVerdict(title, text) {
  els.compareVerdict.innerHTML = `<b>${title}</b><br /><span>${text}</span>`;
  els.compareVerdict.classList.remove("hidden");
}

async function loadMinerTargets() {
  if (!els.minerTargetsGrid || !els.minerStatus) return;
  els.minerStatus.textContent = "Loading miner targets...";
  els.minerStatus.classList.remove("error");
  els.minerTargetsGrid.innerHTML = "";
  if (els.minerEval) {
    els.minerEval.classList.add("hidden");
    els.minerEval.textContent = "";
  }
  if (els.minerTargetSummary) {
    els.minerTargetSummary.classList.add("hidden");
    els.minerTargetSummary.textContent = "";
  }
  try {
    const requestedCount = (() => {
      const n = parseInt((els.minerCount && els.minerCount.value) || "3", 10);
      if (Number.isNaN(n)) return 3;
      return Math.min(Math.max(n, 1), 6);
    })();
    const feeParam = (() => {
      if (!els.minerFee) return "";
      const v = parseFloat(els.minerFee.value);
      if (Number.isNaN(v) || v <= 0) return "";
      return `fee=${v}`;
    })();
    const targetParam = (() => {
      if (!els.targetBlocks) return "";
      const v = parseInt(els.targetBlocks.value || "1", 10);
      if (Number.isNaN(v) || v < 1) return "";
      return `target_blocks=${v}`;
    })();
    const queryParts = [feeParam, targetParam].filter(Boolean);
    const query = queryParts.length ? `?${queryParts.join("&")}` : "";
    const data = await fetchJson(`/mining-target${query}`);
    const blocks = (data.blocks || []).slice(0, requestedCount);
    if (!blocks.length) {
      els.minerStatus.textContent = data.error || "No data available";
      els.minerStatus.classList.add("error");
      return;
    }
    els.minerStatus.textContent = data.cache_used ? "Using cached data" : "Live data";
    if (data.user_fee_eval && els.minerEval) {
      els.minerEval.textContent = data.user_fee_eval.note;
      els.minerEval.classList.remove("hidden");
      if (!data.user_fee_eval.meets_min_fee) {
        els.minerEval.classList.add("error");
      } else {
        els.minerEval.classList.remove("error");
      }
    }
    if (data.target_note && els.minerTargetSummary) {
      els.minerTargetSummary.textContent = data.target_note;
      els.minerTargetSummary.classList.remove("hidden");
    }
    const titles = ["Next Block", "2nd Block", "3rd Block"];
    blocks.forEach((blk, idx) => {
      const card = document.createElement("div");
      card.className = "miner-card";
      if (idx === 0) card.classList.add("highlight");
      card.innerHTML = `
        <h3>${titles[idx] || `Block ${idx + 1}`}</h3>
        <p class="muted">Min Fee to Enter</p>
        <div class="status">${blk.minFee ?? "-"} sat/vB</div>
        <p class="muted">Median Fee: ${blk.medianFee ?? "-"} sat/vB</p>
        <p class="muted">Tx Count: ${(blk.txCount ?? "-").toLocaleString ? (blk.txCount ?? "-").toLocaleString() : (blk.txCount ?? "-")} | Size: ${blk.blockSize ?? "-"} vB</p>
      `;
      els.minerTargetsGrid.appendChild(card);
    });
  } catch (err) {
    console.error("mining-target error", err);
    els.minerStatus.textContent = err.message || "Failed to load mining targets";
    els.minerStatus.classList.add("error");
  }
}

async function handleEstimate() {
  const fee = parseFloat(els.customFee.value);
  const explain = els.explainModeEst.value;
  els.estimateStatus.textContent = "Estimating...";
  els.estimateStatus.classList.remove("error");
  els.estimateResult.classList.add("hidden");
  els.singleResult.classList.add("hidden");

  // Düzeltme: compareResult'ı gizleyen kod kaldırıldı.

  try {
    if (Number.isNaN(fee) || fee <= 0) {
      throw new Error("Enter a fee > 0");
    }
    const explainParam = explain ? `&explain=${explain}` : "";
    const data = await fetchJson(`/estimate?fee=${fee}${explainParam}`);
    const feeLabel = fee.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
    renderRecommendation(els.estimateResult, `Custom fee ${feeLabel} sat/vB`, data);
    els.estimateStatus.textContent = "Done";
  } catch (err) {
    els.estimateStatus.textContent = err.message;
    els.estimateStatus.classList.add("error");
  }
}

async function pollLive() {
  try {
    const data = await fetchJson("/live/status");
    els.liveUpdated.textContent = data.updated_at_epoch
      ? new Date(data.updated_at_epoch * 1000).toLocaleTimeString()
      : "-";
    const mempoolCount = data.mempool_data?.count ?? 0;
    els.liveMempool.textContent = mempoolCount.toLocaleString();
    els.liveFast.textContent = data.fee_data?.fastestFee ?? "-";
    els.liveNormal.textContent = data.fee_data?.halfHourFee ?? "-";
    els.liveCache.classList.toggle("hidden", !data.cache_used);
    els.liveError.classList.toggle("hidden", !data.error);
    els.liveError.textContent = data.error || "";
    if (data.network_state) {
      els.liveState.textContent = data.network_state;
      els.liveState.className = `badge badge-${data.network_state}`;
    }
    els.liveNote.textContent = data.network_note || "";
  } catch (err) {
    els.liveError.textContent = err.message;
    els.liveError.classList.remove("hidden");
  }
}

function activateTab(id) {
  els.tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === id));
  els.tabPanels.forEach((p) => p.classList.toggle("hidden", p.id !== `tab-${id}`));
  if (id === "history") {
    loadHistory();
  }
  if (id === "compare" && !activateTab.compareLoadedOnce) {
    activateTab.compareLoadedOnce = true;
    handleCompare();
  }
  if (id === "miner-targets") {
    loadMinerTargets();
  }
}
activateTab.compareLoadedOnce = false;

async function loadHistory() {
  try {
    const data = await fetchJson("/history");
    const items = data.items || [];
    const insight = data.insight || "";
    if (insight) {
      els.historyInsight.textContent = insight;
      els.historyInsight.classList.remove("hidden");
    } else {
      els.historyInsight.classList.add("hidden");
    }
    if (!items.length) {
      els.historyList.innerHTML = "<p class='muted'>No records found</p>";
      return;
    }
    els.historyList.innerHTML = "";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "history-row";
      row.innerHTML = `
        <div><span>Time</span><b>${item.timestamp || "-"}</b></div>
        <div><span>Priority</span><b>${item.priority}</b></div>
        <div><span>Fee</span><b>${item.recommended_fee_sat_vb} sat/vB</b></div>
        <div><span>Mempool</span><b>${Number(item.mempool_tx_count || 0).toLocaleString()}</b></div>
      `;
      els.historyList.appendChild(row);
    });
  } catch (err) {
    els.historyList.innerHTML = `<p class="status error">${err.message}</p>`;
  }
}

function init() {
  if (els.btnRecommend) els.btnRecommend.addEventListener("click", handleRecommend);
  if (els.btnCompare) els.btnCompare.addEventListener("click", handleCompare);
  if (els.btnEstimate) els.btnEstimate.addEventListener("click", handleEstimate);
  if (els.btnMinerRefresh) els.btnMinerRefresh.addEventListener("click", loadMinerTargets);
  if (els.minerCount) els.minerCount.addEventListener("change", loadMinerTargets);
  if (els.minerFee) els.minerFee.addEventListener("change", loadMinerTargets);
  if (els.targetBlocks) els.targetBlocks.addEventListener("change", loadMinerTargets);
  if (els.tabs && els.tabs.forEach) {
    els.tabs.forEach((tab) =>
      tab.addEventListener("click", () => activateTab(tab.dataset.tab))
    );
  }
  if (els.btnHistory) els.btnHistory.addEventListener("click", loadHistory);
  setStatus("Ready");
  // Preload miner targets once so tab is not empty on first view.
  loadMinerTargets();
  pollLive();
  setInterval(pollLive, 3000);
}

document.addEventListener("DOMContentLoaded", init);
