let state = null;
let lastRequest = null;
let amapInstance = null;
let amapLoadPromise = null;
let amapAvailable = false;
let amapRouteRenderToken = 0;
let amapRoutePlanners = [];
let dailyAmapInstances = new Map();
let dailyMapRenderToken = 0;
let destinationGroups = [];
let destinationNames = [];
let destinationSelected = "上海市";
let filteredDestinationNames = [];
let routeAdvisorPlaces = [];
let amapJsQpsLimit = 10;
const amapJsStarts = [];

const form = document.querySelector("#planForm");
const today = new Date();
document.querySelector("#startDate").valueAsDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 14);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateDestinationSelection()) {
    document.querySelector("#destination").reportValidity();
    openDestinationPicker();
    return;
  }
  await requestPlan();
});

document.querySelector("#exportPdf").addEventListener("click", () => exportBackend("pdf"));
document.querySelector("#exportPng").addEventListener("click", () => exportBackend("image"));
document.querySelector("#compareRoutes").addEventListener("click", compareRouteOptions);

function selectedPreferences() {
  return [...document.querySelectorAll(".preferences input:checked")].map((item) => item.value);
}

function buildRequest() {
  return {
    destination: destinationSelected,
    start_date: document.querySelector("#startDate").value,
    days: Number(document.querySelector("#days").value),
    people: Number(document.querySelector("#people").value),
    budget_level: document.querySelector("#budgetLevel").value,
    transportation: document.querySelector("#transportation").value,
    preferences: selectedPreferences()
  };
}

async function initializeDestinationPicker() {
  const input = document.querySelector("#destination");
  input.disabled = true;
  try {
    const response = await fetch("/api/destinations");
    const payload = await response.json();
    if (!response.ok || payload.success === false || !Array.isArray(payload.data)) {
      throw new Error(payload.message || "目的地目录读取失败");
    }
    destinationGroups = payload.data;
    destinationNames = destinationGroups.flatMap((group) => group.cities || []);
    destinationSelected = destinationNames.includes(input.value) ? input.value : (destinationNames[0] || "");
    input.value = destinationSelected;
    renderDestinationOptions("");
    input.disabled = false;
  } catch (error) {
    input.setCustomValidity("目的地目录加载失败，请刷新页面后重试");
    showError(`目的地目录加载失败：${error.message}`);
  }

  input.addEventListener("focus", () => {
    renderDestinationOptions("");
    openDestinationPicker();
  });
  input.addEventListener("input", () => {
    destinationSelected = "";
    input.setCustomValidity("");
    renderDestinationOptions(input.value.trim());
    openDestinationPicker();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDestinationPicker();
      return;
    }
    if (event.key === "Enter" && !destinationSelected && filteredDestinationNames.length === 1) {
      event.preventDefault();
      selectDestination(filteredDestinationNames[0]);
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".destination-control")) closeDestinationPicker();
  });
}

function renderDestinationOptions(query) {
  const grid = document.querySelector("#destinationGrid");
  const count = document.querySelector("#destinationCount");
  const noResult = document.querySelector("#destinationNoResult");
  const normalizedQuery = String(query || "").trim();
  grid.innerHTML = "";
  filteredDestinationNames = [];

  destinationGroups.forEach((group) => {
    const provinceMatched = matchesProvincePrefix(group.province, normalizedQuery);
    const cities = (group.cities || []).filter((city) => !normalizedQuery || provinceMatched || city.startsWith(normalizedQuery));
    if (!cities.length) return;
    filteredDestinationNames.push(...cities);
    const province = document.createElement("section");
    province.className = "destination-province";
    const heading = document.createElement("h3");
    heading.textContent = group.province;
    const cityGrid = document.createElement("div");
    cityGrid.className = "destination-city-grid";
    cities.forEach((city) => {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", city === destinationSelected ? "true" : "false");
      button.textContent = city;
      button.addEventListener("click", () => selectDestination(city));
      cityGrid.appendChild(button);
    });
    province.append(heading, cityGrid);
    grid.appendChild(province);
  });
  count.textContent = `${filteredDestinationNames.length} 个城市`;
  noResult.hidden = filteredDestinationNames.length > 0;
}

function matchesProvincePrefix(province, query) {
  if (!query) return true;
  const shortName = String(province || "").replace(/特别行政区|维吾尔自治区|壮族自治区|回族自治区|自治区|省$/u, "");
  return String(province || "").startsWith(query) || shortName.startsWith(query);
}
function selectDestination(city) {
  if (!destinationNames.includes(city)) return;
  const input = document.querySelector("#destination");
  destinationSelected = city;
  input.value = city;
  input.setCustomValidity("");
  closeDestinationPicker();
}

function validateDestinationSelection() {
  const input = document.querySelector("#destination");
  const valid = Boolean(destinationSelected && destinationNames.includes(destinationSelected) && input.value === destinationSelected);
  input.setCustomValidity(valid ? "" : "请从省份城市列表或输入提示中选择目的地");
  return valid;
}

function openDestinationPicker() {
  const picker = document.querySelector("#destinationPicker");
  picker.hidden = false;
  document.querySelector("#destination").setAttribute("aria-expanded", "true");
}

function closeDestinationPicker() {
  const picker = document.querySelector("#destinationPicker");
  picker.hidden = true;
  document.querySelector("#destination").setAttribute("aria-expanded", "false");
}
async function loadConfigStatus() {
  const root = document.querySelector("#configStatus");
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    const data = payload.data || {};
    const jsMapMode = data.amap_js_mode === "js_api" ? "JS地图" : "备用地图";
    root.textContent = `高德：${data.amap_mode || "未知"} · ${jsMapMode} · LLM：${data.llm_mode || "未知"} · 模型：${data.llm_model || "未配置"}`;
  } catch (error) {
    root.textContent = "无法读取后端配置状态，请确认 FastAPI 服务正在运行。";
  }
}

async function loadAmapJs() {
  if (amapLoadPromise) return amapLoadPromise;
  amapLoadPromise = (async () => {
    try {
      const response = await fetch("/api/map/js-config");
      const payload = await response.json();
      const config = payload.data || {};
      amapJsQpsLimit = Math.max(1, Math.min(Number(config.qps_limit) || 10, 10));
      if (!config.enabled || !config.key) return false;

      if (config.service_host) {
        window._AMapSecurityConfig = { serviceHost: config.service_host };
      } else if (config.security_js_code) {
        window._AMapSecurityConfig = { securityJsCode: config.security_js_code };
      }

      await appendAmapScript(config.key);
      amapAvailable = Boolean(window.AMap);
      return amapAvailable;
    } catch (error) {
      amapAvailable = false;
      return false;
    }
  })();
  return amapLoadPromise;
}

async function acquireAmapJsSlot() {
  while (true) {
    const now = Date.now();
    while (amapJsStarts.length && now - amapJsStarts[0] >= 1000) amapJsStarts.shift();
    if (amapJsStarts.length < amapJsQpsLimit) {
      amapJsStarts.push(now);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, Math.max(1, 1000 - (now - amapJsStarts[0]))));
  }
}
function appendAmapScript(key) {
  if (window.AMap) return Promise.resolve();
  const existing = document.querySelector("script[data-amap-js]");
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`;
    script.async = true;
    script.dataset.amapJs = "true";
    script.onload = resolve;
    script.onerror = () => reject(new Error("高德地图脚本加载失败"));
    document.head.appendChild(script);
  });
}

async function requestPlan() {
  const button = form.querySelector(".primary");
  lastRequest = buildRequest();
  clearError();
  showProgress(1);
  button.disabled = true;
  button.textContent = "规划中...";
  document.querySelector("#summary").textContent = "多Agent正在协作生成行程。";
  try {
    showProgress(2);
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastRequest)
    });
    showProgress(3);
    const payload = await response.json().catch(() => ({ success: false, message: "响应解析失败" }));
    if (!response.ok || payload.success === false) {
      const detail = payload.error?.detail || payload.detail || payload.message || "请求失败";
      const code = payload.error?.code || `HTTP_${response.status}`;
      throw new Error(`${code}: ${detail}`);
    }
    const data = Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
    state = normalizePlan(data, lastRequest);
    showProgress(4);
    render();
    hideProgressSoon();
  } catch (error) {
    state = null;
    renderEmptyState();
    showError(error.message);
    document.querySelector("#summary").textContent = "行程生成失败，请根据错误提示调整配置或输入。";
  } finally {
    button.disabled = false;
    button.textContent = "生成行程";
  }
}

function showProgress(activeStep) {
  const root = document.querySelector("#progressPanel");
  const steps = ["校验请求参数", "调用多Agent后端", "整合行程与预算", "渲染地图和协作结果"];
  root.style.display = "block";
  root.innerHTML = `<div class="progress-steps">${steps.map((step, index) => {
    const number = index + 1;
    const status = number < activeStep ? "done" : number === activeStep ? "active" : "";
    return `<div class="progress-step ${status}"><i class="progress-dot"></i><span>${step}</span></div>`;
  }).join("")}</div>`;
}

function hideProgressSoon() {
  setTimeout(() => {
    const root = document.querySelector("#progressPanel");
    root.style.display = "none";
  }, 900);
}

function showError(message) {
  const root = document.querySelector("#errorPanel");
  root.style.display = "block";
  root.textContent = message;
}

function clearError() {
  const root = document.querySelector("#errorPanel");
  root.style.display = "none";
  root.textContent = "";
}

function normalizePlan(data, request) {
  const itinerary = data.itinerary || {};
  const days = itinerary.days || [];
  const allSpots = uniqueByName(
    days.flatMap((day) => day.stops || []).filter((stop) => stop.category === "spot")
  );
  return {
    raw: data,
    destination: itinerary.destination || request.destination,
    people: data.budget?.people || request.people,
    preferences: itinerary.preferences || request.preferences,
    transportation: data.transportation || itinerary.transportation || request.transportation || "公共交通",
    days,
    allSpots,
    budget: data.budget || null,
    map: data.map || null,
    summary: data.summary || itinerary.summary || "行程已生成。",
    collaborationTrace: data.collaboration_trace || [],
    topicChecks: data.topic_checks || []
  };
}

function uniqueByName(items) {
  const seen = new Set();
  const output = [];
  items.forEach((item) => {
    if (!item?.name || seen.has(item.name)) return;
    seen.add(item.name);
    output.push(item);
  });
  return output;
}

function render() {
  document.querySelector("#summary").textContent = state.summary;
  renderBudget();
  renderItinerary();
  renderMap();
  renderDailyRouteMaps();
  renderCatalog();
  renderRouteAdvisor();
  renderAgentFlow();
}

function renderEmptyState() {
  document.querySelector("#ticketCost").textContent = "¥0";
  document.querySelector("#hotelCost").textContent = "¥0";
  document.querySelector("#foodCost").textContent = "¥0";
  document.querySelector("#transportCost").textContent = "¥0";
  document.querySelector("#totalCost").textContent = "¥0";
  document.querySelector("#agentFlow").innerHTML = `<div class="empty-state">暂无协作记录。提交表单后会显示每个 Agent 的输入、输出和检查结果。</div>`;
  document.querySelector("#itinerary").innerHTML = `<div class="empty-state">暂无行程。请填写旅行条件并点击“生成行程”。</div>`;
  document.querySelector("#catalog").innerHTML = `<div class="empty-state">暂无可添加景点。</div>`;
  resetRouteAdvisor();
  resetFallbackMap();
  document.querySelector("#routeDistance").textContent = "0 km";
}

function renderAgentFlow() {
  const root = document.querySelector("#agentFlow");
  if (!root) return;
  const trace = state.collaborationTrace.length
    ? state.collaborationTrace
    : [{ step: 1, agent: "多Agent总控", input: "", output: "后端已返回行程结果。" }];
  root.innerHTML = "";
  trace.forEach((item, index) => {
    const check = state.topicChecks.find((entry) => entry.agent === item.agent);
    const passed = !check || check.on_topic;
    const row = document.createElement("div");
    row.className = "agent-step";
    row.innerHTML = `
      <strong>${item.step || index + 1}</strong>
      <div>
        <strong>${item.agent}</strong>
        <div class="agent-io">
          <span>输入：${item.input || "无"}</span>
          <span>输出：${item.output || "无"}</span>
          <span>检查：${check?.reason || "已完成"}</span>
        </div>
      </div>
      <div class="${passed ? "check-ok" : "check-bad"}">${passed ? "通过" : "拦截"}</div>`;
    root.appendChild(row);
  });
}

function renderBudget() {
  const budget = calculateBudget();
  document.querySelector("#ticketCost").textContent = money(budget.ticket);
  document.querySelector("#hotelCost").textContent = money(budget.hotel);
  document.querySelector("#foodCost").textContent = money(budget.food);
  document.querySelector("#transportCost").textContent = money(budget.transport);
  document.querySelector("#totalCost").textContent = money(budget.total);
}

function calculateBudget() {
  if (!state) return { ticket: 0, hotel: 0, food: 0, transport: 0, total: 0 };
  const people = state.people || 1;
  const ticket = state.days.flatMap((day) => day.stops || []).reduce((sum, stop) => sum + (stop.ticket || 0) * people, 0);
  const food = state.days.flatMap((day) => day.stops || []).reduce((sum, stop) => sum + (stop.category === "restaurant" ? (stop.price || 80) * people : 0), 0);
  const hotel = state.days.slice(0, Math.max(1, state.days.length - 1)).reduce((sum, day) => sum + (day.hotel?.price || 0), 0);
  const mode = routeTypeFromTransportation();
  const baseTransport = mode === "walking" ? 20 : mode === "driving" ? 120 : 50;
  const transport = state.days.length * people * baseTransport;
  return { ticket, food, hotel, transport, total: ticket + food + hotel + transport };
}

function money(value) {
  return `¥${Number(value || 0).toLocaleString("zh-CN")}`;
}

function renderItinerary() {
  const root = document.querySelector("#itinerary");
  clearDailyAmapInstances();
  root.innerHTML = "";
  if (!state.days.length) {
    root.innerHTML = `<div class="empty-state">后端没有返回每日行程。</div>`;
    return;
  }
  state.days.forEach((day, dayIndex) => {
    const routeView = document.createElement("article");
    routeView.className = "daily-route-view";
    routeView.innerHTML = `
      <section class="daily-map-block" aria-label="第 ${day.day} 天路线图">
        <div class="daily-map-head">
          <strong>第 ${day.day} 天路线图</strong>
          <span id="dayRouteDistance-${dayIndex}">0 km</span>
        </div>
        <div id="dayMap-${dayIndex}" class="daily-map-canvas map-canvas">
          <svg id="dayFallbackMap-${dayIndex}" class="daily-fallback-map" viewBox="0 0 720 520"></svg>
        </div>
      </section>`;

    const section = document.createElement("section");
    section.className = "day";
    const hotelName = day.hotel?.name || "待定酒店";
    const hotelPrice = day.hotel?.price || 0;
    section.innerHTML = `<header><h2>第 ${day.day} 天 · ${day.date}</h2><div class="hotel">${hotelName} · ¥${hotelPrice}/晚</div></header>`;
    (day.stops || []).forEach((stop, stopIndex) => {
      const row = document.createElement("div");
      row.className = "stop";
      row.innerHTML = `
        <div class="time">${stop.time || "--:--"}</div>
        <div>
          <div class="stop-title">${stop.name}</div>
          <div class="stop-reason">${stop.reason || "根据当天偏好和路线自动安排。"}</div>
        </div>
        <div class="stop-actions">
          <button type="button" title="上移">↑</button>
          <button type="button" title="下移">↓</button>
          <button type="button" title="删除">×</button>
        </div>`;
      const [up, down, remove] = row.querySelectorAll("button");
      up.addEventListener("click", () => moveStop(dayIndex, stopIndex, -1));
      down.addEventListener("click", () => moveStop(dayIndex, stopIndex, 1));
      remove.addEventListener("click", () => removeStop(dayIndex, stopIndex));
      section.appendChild(row);
    });
    routeView.appendChild(section);
    root.appendChild(routeView);
  });
}

async function moveStop(dayIndex, stopIndex, direction) {
  const stops = state.days[dayIndex].stops;
  const target = stopIndex + direction;
  if (target < 0 || target >= stops.length) return;
  await syncEdit({ action: "move", day_index: dayIndex, stop_index: stopIndex, target_index: target });
}

async function removeStop(dayIndex, stopIndex) {
  await syncEdit({ action: "delete", day_index: dayIndex, stop_index: stopIndex });
}

async function addSpot(spotName) {
  const spot = state.allSpots.find((item) => item.name === spotName);
  if (!spot || !state.days[0]) return;
  await syncEdit({ action: "add", day_index: 0, stop: { ...spot, category: "spot", time: "15:30" } });
}

async function syncEdit(payload) {
  if (!state?.raw) return;
  clearError();
  try {
    const response = await fetch("/api/trip/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: state.raw, ...payload })
    });
    const result = await response.json();
    if (!response.ok || result.success === false) {
      throw new Error(result.error?.detail || result.message || "编辑失败");
    }
    state = normalizePlan(result.data, lastRequest || buildRequest());
    render();
  } catch (error) {
    showError(`编辑失败：${error.message}`);
  }
}

async function exportBackend(kind) {
  if (!state?.raw) {
    showError("暂无可导出的行程，请先生成行程。");
    return;
  }
  const endpoint = kind === "pdf" ? "/api/export/pdf" : "/api/export/image";
  const filename = kind === "pdf" ? `${state.destination}-旅行计划.pdf` : `${state.destination}-路线图.svg`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: state.raw })
    });
    if (!response.ok) throw new Error("导出失败");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showError(`导出失败：${error.message}`);
  }
}

function renderCatalog() {
  const root = document.querySelector("#catalog");
  root.innerHTML = "";
  if (!state.allSpots.length) {
    root.innerHTML = `<div class="empty-state">当前行程没有可重复添加的景点。</div>`;
    return;
  }
  state.allSpots.forEach((spot) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `+ ${spot.name}`;
    button.addEventListener("click", () => addSpot(spot.name));
    root.appendChild(button);
  });
}

function renderRouteAdvisor() {
  const originSelect = document.querySelector("#routeOrigin");
  const destinationSelect = document.querySelector("#routeDestination");
  const compareButton = document.querySelector("#compareRoutes");
  routeAdvisorPlaces = uniqueByName(collectMarkers());
  originSelect.innerHTML = "";
  destinationSelect.innerHTML = "";
  routeAdvisorPlaces.forEach((place, index) => {
    const originOption = new Option(place.name, String(index));
    const destinationOption = new Option(place.name, String(index));
    originSelect.add(originOption);
    destinationSelect.add(destinationOption);
  });
  const ready = routeAdvisorPlaces.length >= 2;
  originSelect.disabled = !ready;
  destinationSelect.disabled = !ready;
  compareButton.disabled = !ready;
  if (ready) {
    originSelect.value = "0";
    destinationSelect.value = "1";
  }
  document.querySelector("#routeAdvisorResult").innerHTML = ready
    ? `<div class="empty-state">选择起点、终点和交通方式后开始比较。</div>`
    : `<div class="empty-state">当前行程地点不足，暂时无法比较路线。</div>`;
}

function resetRouteAdvisor() {
  routeAdvisorPlaces = [];
  document.querySelector("#routeOrigin").innerHTML = "";
  document.querySelector("#routeDestination").innerHTML = "";
  document.querySelector("#routeOrigin").disabled = true;
  document.querySelector("#routeDestination").disabled = true;
  document.querySelector("#compareRoutes").disabled = true;
  document.querySelector("#routeAdvisorResult").innerHTML = `<div class="empty-state">生成行程后可选择两个地点进行交通方式比较。</div>`;
}

function selectedRouteModes() {
  return [...document.querySelectorAll(".route-mode-options input:checked")].map((input) => input.value);
}

async function compareRouteOptions() {
  const resultRoot = document.querySelector("#routeAdvisorResult");
  const button = document.querySelector("#compareRoutes");
  const origin = routeAdvisorPlaces[Number(document.querySelector("#routeOrigin").value)];
  const destination = routeAdvisorPlaces[Number(document.querySelector("#routeDestination").value)];
  const modes = selectedRouteModes();
  if (!origin || !destination) {
    showError("请选择有效的起点和终点。");
    return;
  }
  if (origin.name === destination.name) {
    showError("起点和终点不能相同。");
    return;
  }
  if (!modes.length) {
    showError("请至少勾选一种交通方式。");
    return;
  }
  clearError();
  button.disabled = true;
  button.textContent = "比较中...";
  resultRoot.innerHTML = `<div class="empty-state">路线规划专家正在比较时间、费用和舒适度...</div>`;
  try {
    const response = await fetch("/api/route/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: state.destination,
        origin: { name: origin.name, lat: Number(origin.lat), lng: Number(origin.lng) },
        destination: { name: destination.name, lat: Number(destination.lat), lng: Number(destination.lng) },
        selected_modes: modes,
        priority: document.querySelector("#routePriority").value,
        people: state.people || 1
      })
    });
    const payload = await response.json();
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error?.detail || payload.message || "路线比较失败");
    }
    renderRouteRecommendation(payload.data);
  } catch (error) {
    resultRoot.innerHTML = `<div class="empty-state">路线比较失败，请稍后重试。</div>`;
    showError(`路线比较失败：${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = "比较并推荐";
  }
}

function renderRouteRecommendation(data) {
  const root = document.querySelector("#routeAdvisorResult");
  root.innerHTML = "";
  const summary = document.createElement("div");
  summary.className = "route-recommendation-summary";
  const agent = document.createElement("strong");
  agent.textContent = `${data.agent}推荐：${data.recommended_label}`;
  const reason = document.createElement("span");
  reason.textContent = data.recommendation;
  summary.append(agent, reason);
  const options = document.createElement("div");
  options.className = "route-option-grid";
  (data.options || []).forEach((option) => {
    const item = document.createElement("article");
    item.className = `route-option route-option-${option.mode}${option.recommended ? " recommended" : ""}`;
    const title = document.createElement("div");
    title.className = "route-option-title";
    title.innerHTML = `<strong>${option.label}</strong><span>${option.recommended ? "最佳" : `评分 ${option.score}`}</span>`;
    const metrics = document.createElement("div");
    metrics.className = "route-option-metrics";
    metrics.innerHTML = `<span>${option.duration_minutes} 分钟</span><span>¥${Number(option.estimated_cost).toFixed(2)}</span><span>${Number(option.distance_km).toFixed(1)} km</span>`;
    const detail = document.createElement("p");
    detail.textContent = [...(option.pros || []), ...(option.cons || []).map((text) => `注意：${text}`)].join("；");
    item.append(title, metrics, detail);
    options.appendChild(item);
  });
  root.append(summary, options);
}
function renderMap() {
  const markers = collectMarkers();
  renderFallbackMap(markers);
  document.querySelector("#routeDistance").textContent = `${calculateDistance(markers).toFixed(1)} km`;
  if (!markers.length) return;

  loadAmapJs().then((ready) => {
    if (ready) renderAmap(markers);
  });
}

function renderDailyRouteMaps() {
  if (!state?.days?.length) return;
  const token = ++dailyMapRenderToken;
  state.days.forEach((day, dayIndex) => {
    const markers = collectDayMarkers(day);
    const svg = document.querySelector(`#dayFallbackMap-${dayIndex}`);
    const distanceElement = document.querySelector(`#dayRouteDistance-${dayIndex}`);
    if (!svg) return;
    renderFallbackMapContent(svg, markers, `dayRouteArrow-${dayIndex}`);
    if (distanceElement) distanceElement.textContent = `${calculateDistance(markers).toFixed(1)} km`;
    if (!markers.length) return;
    loadAmapJs().then((ready) => {
      if (ready && token === dailyMapRenderToken) {
        renderDailyAmap(dayIndex, markers, distanceElement, token);
      }
    });
  });
}

async function renderDailyAmap(dayIndex, markers, distanceElement, token) {
  if (!window.AMap || !markers.length || token !== dailyMapRenderToken) return;
  await acquireAmapJsSlot();
  if (token !== dailyMapRenderToken) return;
  const containerId = `dayMap-${dayIndex}`;
  const container = document.querySelector(`#${containerId}`);
  if (!container) return;
  const map = new window.AMap.Map(containerId, {
    zoom: 12,
    center: [Number(markers[0].lng), Number(markers[0].lat)],
    viewMode: "2D"
  });
  dailyAmapInstances.set(dayIndex, map);
  markers.forEach((marker, index) => {
    map.add(new window.AMap.Marker({
      position: [Number(marker.lng), Number(marker.lat)],
      title: marker.name,
      label: { direction: "right", content: `${index + 1}. ${marker.name}` }
    }));
  });
  container.classList.add("amap-ready");
  renderDailyRoadRoute(map, markers, distanceElement, token);
}

async function renderDailyRoadRoute(map, markers, distanceElement, token) {
  const straightPath = markers.map((marker) => [Number(marker.lng), Number(marker.lat)]);
  if (straightPath.length < 2) {
    map.setFitView(null, false, [42, 42, 42, 42]);
    return;
  }
  try {
    const summary = await fetchRouteSummary(markers, distanceElement);
    if (token !== dailyMapRenderToken) return;
    const routePath = Array.isArray(summary?.polyline) && summary.polyline.length > 1 ? summary.polyline : straightPath;
    drawAmapRoute(map, routePath);
  } catch (error) {
    if (token === dailyMapRenderToken) drawAmapRoute(map, straightPath);
  }
  if (token === dailyMapRenderToken) map.setFitView(null, false, [42, 42, 42, 42]);
}

function clearDailyAmapInstances() {
  dailyMapRenderToken += 1;
  dailyAmapInstances.forEach((map) => {
    if (typeof map.destroy === "function") map.destroy();
  });
  dailyAmapInstances.clear();
}
async function renderAmap(markers) {
  if (!window.AMap || !markers.length) return;
  const container = document.querySelector("#map");
  const center = [Number(markers[0].lng), Number(markers[0].lat)];
  if (!amapInstance) {
    await acquireAmapJsSlot();
    amapInstance = new window.AMap.Map("map", {
      zoom: 12,
      center,
      viewMode: "2D"
    });
  }
  clearAmapRoutePlanners();
  amapRouteRenderToken += 1;
  const token = amapRouteRenderToken;
  amapInstance.clearMap();

  markers.forEach((marker, index) => {
    const pin = new window.AMap.Marker({
      position: [Number(marker.lng), Number(marker.lat)],
      title: marker.name,
      label: {
        direction: "right",
        content: `${index + 1}. ${marker.name}`
      }
    });
    amapInstance.add(pin);
  });

  renderRoadRoute(markers, token);
  container.classList.add("amap-ready");
  amapAvailable = true;
}

async function renderRoadRoute(markers, token) {
  const straightPath = markers.map((marker) => [Number(marker.lng), Number(marker.lat)]);
  if (straightPath.length < 2) {
    amapInstance.setFitView(null, false, [48, 48, 48, 48]);
    return;
  }

  try {
    const summary = await fetchRouteSummary(markers);
    if (token !== amapRouteRenderToken) return;
    const routePath = Array.isArray(summary?.polyline) && summary.polyline.length > 1 ? summary.polyline : straightPath;
    drawStraightAmapRoute(routePath);
    amapInstance.setFitView(null, false, [48, 48, 48, 48]);
  } catch (error) {
    if (token === amapRouteRenderToken) {
      drawStraightAmapRoute(straightPath);
      amapInstance.setFitView(null, false, [48, 48, 48, 48]);
    }
  }
}


function routeStyle() {
  const mode = routeTypeFromTransportation();
  if (mode === "driving") return { color: "#d84e2f", label: "驾车" };
  if (mode === "walking") return { color: "#2f8f5b", label: "步行" };
  if (mode === "cycling") return { color: "#8a5a00", label: "共享单车" };
  return { color: "#2f5fd0", label: "公共交通" };
}
function routeTypeFromTransportation() {
  const value = state?.transportation || lastRequest?.transportation || document.querySelector("#transportation")?.value || "公共交通";
  if (/驾车|自驾|开车|打车|出租/.test(value)) return "driving";
  if (/步行|徒步|walk/i.test(value)) return "walking";
  if (/共享单车|骑行|自行车|bike/i.test(value)) return "cycling";
  return "transit";
}

async function fetchRouteSummary(markers, distanceElement = document.querySelector("#routeDistance")) {
  const requestBody = {
    route_type: routeTypeFromTransportation(),
    city: state?.destination || lastRequest?.destination || document.querySelector("#destination")?.value || "",
    points: markers.map((marker) => ({ name: marker.name, lat: Number(marker.lat), lng: Number(marker.lng) }))
  };
  let lastError = null;
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      const response = await fetch("/api/map/route-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });
      const payload = await response.json();
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error?.detail || payload.message || "路线规划失败");
      }
      if (payload.data?.distance_km) {
        if (distanceElement) distanceElement.textContent = `${Number(payload.data.distance_km).toFixed(1)} km`;
      }
      return payload.data;
    } catch (error) {
      lastError = error;
      if (attempt < 5) await delay(180 * attempt);
    }
  }
  throw lastError || new Error("路线规划失败");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
function drawStraightAmapRoute(path) {
  drawAmapRoute(amapInstance, path);
}

function drawAmapRoute(map, path) {
  const style = routeStyle();
  const casing = new window.AMap.Polyline({
    path,
    strokeColor: "#ffffff",
    strokeWeight: 7,
    strokeOpacity: 0.72,
    lineJoin: "round",
    lineCap: "round",
    zIndex: 48
  });
  const polyline = new window.AMap.Polyline({
    path,
    strokeColor: style.color,
    strokeWeight: 4,
    strokeOpacity: 0.95,
    lineJoin: "round",
    lineCap: "round",
    showDir: true,
    dirColor: style.color,
    zIndex: 50
  });
  map.add([casing, polyline]);
}
function clearAmapRoutePlanners() {
  amapRoutePlanners.forEach((planner) => {
    if (typeof planner.clear === "function") planner.clear();
  });
  amapRoutePlanners = [];
}
function renderFallbackMap(markers) {
  const svg = ensureFallbackMap();
  const container = document.querySelector("#map");
  container.classList.remove("amap-ready");
  svg.innerHTML = "";
  if (!markers.length) return;

  const points = markers.map((marker) => project(marker, markers));
  const style = routeStyle();
  appendSvgArrowDef(svg, style.color);
  const casing = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  casing.setAttribute("class", "route-casing");
  casing.setAttribute("points", points.map((point) => point.join(",")).join(" "));
  svg.appendChild(casing);
  const route = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  route.setAttribute("class", "route");
  route.setAttribute("stroke", style.color);
  route.setAttribute("marker-end", "url(#routeArrow)");
  route.setAttribute("points", points.map((point) => point.join(",")).join(" "));
  svg.appendChild(route);
  appendRouteDirectionHints(svg, points, style.color);

  markers.forEach((marker, index) => {
    const [x, y] = points[index];
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "marker");
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("class", "pin");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", marker.category === "hotel" ? 12 : 10);
    circle.setAttribute("fill", colorFor(marker.category));
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x + 14);
    text.setAttribute("y", y + 5);
    text.textContent = marker.name;
    group.append(circle, text);
    svg.appendChild(group);
  });
}


function renderFallbackMapContent(svg, markers, arrowId) {
  svg.innerHTML = "";
  if (!markers.length) return;
  const points = markers.map((marker) => project(marker, markers));
  const style = routeStyle();
  appendSvgArrowDef(svg, style.color, arrowId);
  const casing = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  casing.setAttribute("class", "route-casing");
  casing.setAttribute("points", points.map((point) => point.join(",")).join(" "));
  svg.appendChild(casing);
  const route = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  route.setAttribute("class", "route");
  route.setAttribute("stroke", style.color);
  route.setAttribute("marker-end", `url(#${arrowId})`);
  route.setAttribute("points", points.map((point) => point.join(",")).join(" "));
  svg.appendChild(route);
  appendRouteDirectionHints(svg, points, style.color);
  markers.forEach((marker, index) => {
    const [x, y] = points[index];
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "marker");
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("class", "pin");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", marker.category === "hotel" ? 12 : 10);
    circle.setAttribute("fill", colorFor(marker.category));
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x + 14);
    text.setAttribute("y", y + 5);
    text.textContent = marker.name;
    group.append(circle, text);
    svg.appendChild(group);
  });
}
function appendSvgArrowDef(svg, color, markerId = "routeArrow") {
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
  marker.setAttribute("id", markerId);
  marker.setAttribute("markerWidth", "8");
  marker.setAttribute("markerHeight", "8");
  marker.setAttribute("refX", "7");
  marker.setAttribute("refY", "4");
  marker.setAttribute("orient", "auto");
  marker.setAttribute("markerUnits", "strokeWidth");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M 0 0 L 8 4 L 0 8 z");
  path.setAttribute("fill", color);
  marker.appendChild(path);
  defs.appendChild(marker);
  svg.appendChild(defs);
}

function appendRouteDirectionHints(svg, points, color) {
  points.slice(1, -1).forEach((point, index) => {
    if (index % 2 !== 0) return;
    const previous = points[index];
    const angle = Math.atan2(point[1] - previous[1], point[0] - previous[0]) * 180 / Math.PI;
    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrow.setAttribute("d", "M -5 -3 L 4 0 L -5 3");
    arrow.setAttribute("fill", "none");
    arrow.setAttribute("stroke", color);
    arrow.setAttribute("stroke-width", "2");
    arrow.setAttribute("stroke-linecap", "round");
    arrow.setAttribute("transform", `translate(${point[0]} ${point[1]}) rotate(${angle})`);
    svg.appendChild(arrow);
  });
}
function ensureFallbackMap() {
  const container = document.querySelector("#map");
  let svg = document.querySelector("#fallbackMap");
  if (!svg) {
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("id", "fallbackMap");
    svg.setAttribute("viewBox", "0 0 720 520");
    container.prepend(svg);
  }
  return svg;
}

function resetFallbackMap() {
  if (amapInstance) {
    amapInstance.clearMap();
  }
  clearDailyAmapInstances();
  const container = document.querySelector("#map");
  container.classList.remove("amap-ready");
  ensureFallbackMap().innerHTML = "";
}

function collectDayMarkers(day) {
  if (!day) return [];
  return [{ ...(day.hotel || {}), category: "hotel" }, ...(day.stops || [])]
    .filter((item) => Number(item.lat) && Number(item.lng));
}
function collectMarkers() {
  if (!state) return [];
  return state.days.flatMap((day) => [{ ...(day.hotel || {}), category: "hotel" }, ...(day.stops || [])])
    .filter((item) => Number(item.lat) && Number(item.lng));
}

function project(item, markers) {
  const lats = markers.map((marker) => Number(marker.lat));
  const lngs = markers.map((marker) => Number(marker.lng));
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const x = 70 + ((Number(item.lng) - minLng) / Math.max(0.001, maxLng - minLng)) * 580;
  const y = 70 + ((maxLat - Number(item.lat)) / Math.max(0.001, maxLat - minLat)) * 380;
  return [x, y];
}

function colorFor(category) {
  if (category === "hotel") return "#c65b7c";
  if (category === "restaurant") return "#f2a541";
  return "#087f8c";
}

function calculateDistance(markers) {
  let total = 0;
  for (let index = 1; index < markers.length; index += 1) {
    total += haversine(markers[index - 1], markers[index]);
  }
  return total;
}

function haversine(a, b) {
  const radius = 6371;
  const dLat = radians(Number(b.lat) - Number(a.lat));
  const dLng = radians(Number(b.lng) - Number(a.lng));
  const value = Math.sin(dLat / 2) ** 2 + Math.cos(radians(Number(a.lat))) * Math.cos(radians(Number(b.lat))) * Math.sin(dLng / 2) ** 2;
  return radius * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
}

function radians(value) {
  return value * Math.PI / 180;
}

function exportMapPng() {
  const svg = ensureFallbackMap();
  const data = new XMLSerializer().serializeToString(svg);
  const image = new Image();
  const blob = new Blob([data], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  image.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = 1440;
    canvas.height = 1040;
    const context = canvas.getContext("2d");
    context.fillStyle = "#eef6f4";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    const link = document.createElement("a");
    link.download = `${state?.destination || "旅行"}-路线地图.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };
  image.src = url;
}

initializeDestinationPicker();
loadConfigStatus();
loadAmapJs();
renderEmptyState();









