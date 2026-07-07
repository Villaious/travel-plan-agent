let state = null;
let lastRequest = null;

const form = document.querySelector("#planForm");
const today = new Date();
document.querySelector("#startDate").valueAsDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 14);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await requestPlan();
});

document.querySelector("#exportPdf").addEventListener("click", () => exportBackend("pdf"));
document.querySelector("#exportPng").addEventListener("click", () => exportBackend("image"));

function selectedPreferences() {
  return [...document.querySelectorAll(".preferences input:checked")].map((item) => item.value);
}

function buildRequest() {
  return {
    destination: document.querySelector("#destination").value,
    start_date: document.querySelector("#startDate").value,
    days: Number(document.querySelector("#days").value),
    people: Number(document.querySelector("#people").value),
    budget_level: document.querySelector("#budgetLevel").value,
    preferences: selectedPreferences()
  };
}

async function loadConfigStatus() {
  const root = document.querySelector("#configStatus");
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    const data = payload.data || {};
    root.textContent = `高德：${data.amap_mode || "未知"} · LLM：${data.llm_mode || "未知"} · 模型：${data.llm_model || "未配置"}`;
  } catch (error) {
    root.textContent = "无法读取后端配置状态，请确认 FastAPI 服务正在运行。";
  }
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
  renderCatalog();
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
  document.querySelector("#map").innerHTML = "";
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
  const transport = state.days.length * people * 80;
  return { ticket, food, hotel, transport, total: ticket + food + hotel + transport };
}

function money(value) {
  return `¥${Number(value || 0).toLocaleString("zh-CN")}`;
}

function renderItinerary() {
  const root = document.querySelector("#itinerary");
  root.innerHTML = "";
  if (!state.days.length) {
    root.innerHTML = `<div class="empty-state">后端没有返回每日行程。</div>`;
    return;
  }
  state.days.forEach((day, dayIndex) => {
    const section = document.createElement("article");
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
    root.appendChild(section);
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

function refreshTimes(stops) {
  const times = ["09:00", "11:00", "12:30", "14:30", "16:00", "18:00", "19:30"];
  stops.forEach((stop, index) => {
    stop.time = times[index] || "20:30";
  });
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

function renderMap() {
  const svg = document.querySelector("#map");
  svg.innerHTML = "";
  const markers = collectMarkers();
  if (!markers.length) {
    document.querySelector("#routeDistance").textContent = "0 km";
    return;
  }
  const points = markers.map((marker) => project(marker, markers));
  const route = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  route.setAttribute("class", "route");
  route.setAttribute("points", points.map((point) => point.join(",")).join(" "));
  svg.appendChild(route);

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

  document.querySelector("#routeDistance").textContent = `${calculateDistance(markers).toFixed(1)} km`;
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
  const svg = document.querySelector("#map");
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

loadConfigStatus();
renderEmptyState();

