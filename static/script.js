// ── State ──────────────────────────────────────────────────
let habits = [],
  logs = [],
  currentDate = new Date();
let selectedColor = "#a78bfa";

const $ = (id) => document.getElementById(id);

// ── Init ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  updateMonthLabel();
  loadAll();
  bindNav();
  bindModal();
  $("prevMonth").onclick = () => {
    currentDate.setMonth(currentDate.getMonth() - 1);
    onMonthChange();
  };
  $("nextMonth").onclick = () => {
    currentDate.setMonth(currentDate.getMonth() + 1);
    onMonthChange();
  };
  $("todayDate").textContent = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
});

async function loadAll() {
  const [h, l, s] = await Promise.all([
    fetch("/api/habits").then((r) => r.json()),
    fetch(`/api/logs?month=${ym()}`).then((r) => r.json()),
    fetch("/api/stats").then((r) => r.json()),
  ]);
  habits = h;
  logs = l;
  renderDashboard(s);
  renderTracker();
  renderStats();
}

function onMonthChange() {
  updateMonthLabel();
  fetch(`/api/logs?month=${ym()}`)
    .then((r) => r.json())
    .then((l) => {
      logs = l;
      renderTracker();
      renderStats();
    });
}

// ── Helpers ─────────────────────────────────────────────────
const ym = () =>
  `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`;
const today = () => new Date().toISOString().slice(0, 10);
const daysInMonth = () =>
  new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).getDate();
const dateStr = (d) => `${ym()}-${String(d).padStart(2, "0")}`;
const isDone = (hid, d) =>
  logs.some((l) => l.habit_id === hid && l.date === dateStr(d));

function updateMonthLabel() {
  $("monthLabel").textContent = currentDate.toLocaleString("default", {
    month: "short",
    year: "numeric",
  });
}

// ── Tab Nav ─────────────────────────────────────────────────
function bindNav() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.onclick = () => {
      document
        .querySelectorAll(".nav-btn")
        .forEach((b) => b.classList.remove("active"));
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      btn.classList.add("active");
      $(`tab-${btn.dataset.tab}`).classList.add("active");
    };
  });
}

// ── Dashboard ───────────────────────────────────────────────
function renderDashboard(s) {
  $("statDoneToday").textContent = s.done_today;
  $("statTotal").textContent = s.total_habits;
  $("statMonthLogs").textContent = s.month_logs;
  const pct = s.total_habits
    ? Math.round((s.done_today / s.total_habits) * 100)
    : 0;
  $("statPct").textContent = pct + "%";

  // Donut
  const circ = 2 * Math.PI * 80;
  const offset = circ - (pct / 100) * circ;
  $("donutArc").style.strokeDasharray = circ;
  $("donutArc").style.strokeDashoffset = offset;
  $("donutText").textContent = `${s.done_today}/${s.total_habits}`;

  // Today list
  const todayStr = today();
  const wrap = $("todayHabits");
  wrap.innerHTML = "";
  if (!habits.length) {
    wrap.innerHTML =
      '<p style="color:#64748b">No habits yet. Add some in the Tracker tab!</p>';
    return;
  }
  habits.forEach((h) => {
    const done = logs.some((l) => l.habit_id === h.id && l.date === todayStr);
    const div = document.createElement("div");
    div.className = `today-item${done ? " done" : ""}`;
    div.style.setProperty("--hcolor", h.color);
    div.innerHTML = `
      <div class="check">${done ? "✓" : ""}</div>
      <span class="habit-icon">${h.icon}</span>
      <span class="hname">${h.name}</span>
      <button class="del-btn" data-id="${h.id}" title="Delete habit">🗑</button>`;
    div.onclick = async (e) => {
      if (e.target.classList.contains("del-btn")) return;
      await toggleLog(h.id, todayStr);
    };
    div.querySelector(".del-btn").onclick = (e) => {
      e.stopPropagation();
      deleteHabit(h.id);
    };
    wrap.appendChild(div);
  });
}

// ── Tracker Grid ────────────────────────────────────────────
function renderTracker() {
  const wrap = $("trackerGrid");
  if (!habits.length) {
    wrap.innerHTML =
      '<p style="color:#64748b;padding:16px">No habits yet. Click "+ Add Habit" to start!</p>';
    return;
  }

  const days = daysInMonth();
  const todayFull = today();
  const todayDay = parseInt(todayFull.slice(8));
  const isCurrentMonth = ym() === todayFull.slice(0, 7);

  let html = `<table class="tracker-table"><thead><tr>
    <th style="text-align:left;padding:8px 12px">Habit</th>`;
  for (let d = 1; d <= days; d++) {
    const dt = new Date(currentDate.getFullYear(), currentDate.getMonth(), d);
    const dow = dt.getDay();
    const isToday = isCurrentMonth && d === todayDay;
    html += `<th class="${isToday ? "today-col" : ""} ${dow === 0 || dow === 6 ? "weekend-col" : ""}">${d}</th>`;
  }
  html += `<th>Done</th><th>Goal</th></tr></thead><tbody>`;

  habits.forEach((h) => {
    let done = 0;
    html += `<tr><td class="habit-name-cell"><span class="habit-icon">${h.icon}</span>${h.name}</td>`;
    for (let d = 1; d <= days; d++) {
      const dt = new Date(currentDate.getFullYear(), currentDate.getMonth(), d);
      const dow = dt.getDay();
      const isToday = isCurrentMonth && d === todayDay;
      const checked = isDone(h.id, d);
      if (checked) done++;
      html += `<td class="day-cell ${isToday ? "today-col" : ""} ${dow === 0 || dow === 6 ? "weekend-col" : ""}">
        <button class="day-btn${checked ? " done" : ""}"
          style="${checked ? `background:${h.color}` : "color:transparent"}"
          data-hid="${h.id}" data-d="${d}">✓</button></td>`;
    }
    const pct = Math.round((done / days) * 100);
    html += `<td style="font-weight:700;color:${h.color}">${done}</td>
             <td style="color:#64748b;font-size:.8rem">${h.goal}</td></tr>`;
  });
  html += "</tbody></table>";
  wrap.innerHTML = html;

  wrap.querySelectorAll(".day-btn").forEach((btn) => {
    btn.onclick = () => toggleLog(+btn.dataset.hid, dateStr(+btn.dataset.d));
  });
}

// ── Stats ────────────────────────────────────────────────────
function renderStats() {
  const days = daysInMonth();
  const wrap = $("statsCards");
  wrap.innerHTML = "";
  habits.forEach((h) => {
    const done = logs.filter((l) => l.habit_id === h.id).length;
    const pct = Math.round((done / days) * 100);
    wrap.innerHTML += `
      <div class="stat-card" style="--hcolor:${h.color}">
        <h3>${h.icon} ${h.name}</h3>
        <div class="progress-bar-wrap">
          <div class="progress-bar" style="width:${pct}%"></div>
        </div>
        <div class="stat-meta">
          <span>✅ ${done} / ${days} days</span>
          <span>🎯 Goal: ${h.goal}</span>
          <span>📊 ${pct}%</span>
        </div>
      </div>`;
  });
  if (!habits.length)
    wrap.innerHTML = '<p style="color:#64748b">No habits to show.</p>';
}

// ── Toggle Log ───────────────────────────────────────────────
async function toggleLog(habitId, date) {
  const res = await fetch("/api/log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ habit_id: habitId, date }),
  }).then((r) => r.json());

  // Update local logs
  if (res.done) {
    logs.push({ habit_id: habitId, date });
  } else {
    logs = logs.filter((l) => !(l.habit_id === habitId && l.date === date));
  }

  const s = await fetch("/api/stats").then((r) => r.json());
  renderDashboard(s);
  renderTracker();
  renderStats();
}

// ── Delete Habit ─────────────────────────────────────────────
async function deleteHabit(id) {
  if (!confirm("Delete this habit and all its logs?")) return;
  await fetch(`/api/habits/${id}`, { method: "DELETE" });
  await loadAll();
}

// ── Modal ────────────────────────────────────────────────────
function bindModal() {
  $("openModal").onclick = () => $("modal").classList.remove("hidden");
  $("closeModal").onclick = () => $("modal").classList.add("hidden");
  $("modal").onclick = (e) => {
    if (e.target === $("modal")) $("modal").classList.add("hidden");
  };

  document.querySelectorAll(".color-opt").forEach((opt) => {
    opt.onclick = () => {
      document
        .querySelectorAll(".color-opt")
        .forEach((o) => o.classList.remove("selected"));
      opt.classList.add("selected");
      selectedColor = opt.dataset.c;
      $("mColor").value = selectedColor;
    };
  });
  $("mColor").oninput = (e) => {
    selectedColor = e.target.value;
  };
  // default select first color
  document.querySelector(".color-opt").classList.add("selected");

  $("saveHabit").onclick = async () => {
    const name = $("mName").value.trim();
    if (!name) return alert("Please enter a habit name!");
    await fetch("/api/habits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        icon: $("mIcon").value.trim() || "⭐",
        color: selectedColor,
        goal: parseInt($("mGoal").value) || 30,
      }),
    });
    $("mName").value = "";
    $("mIcon").value = "";
    $("modal").classList.add("hidden");
    await loadAll();
  };
}
