const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const rangesList = document.getElementById("ranges-list");
const blockedDatesList = document.getElementById("blocked-dates-list");
const weekdayGrid = document.getElementById("weekday-grid");
const examClassBtns = document.querySelectorAll("#exam-class .seg-btn");
const form = document.getElementById("config-form");

let examClass = 7;

// ---------- dynamic rows ----------

function createRangeRow(start, end) {
  const row = document.createElement("div");
  row.className = "range-row";
  row.innerHTML = `
    <label>From (blank = earliest eligible date)
      <input type="date" class="range-start" value="${start || ""}" />
    </label>
    <label>Until
      <input type="date" class="range-end" value="${end || ""}" required />
    </label>
    <button type="button" class="btn-icon remove-range" title="Remove range">✕</button>
  `;
  row.querySelector(".remove-range").addEventListener("click", () => row.remove());
  rangesList.appendChild(row);
}

function createBlockedDateRow(value) {
  const row = document.createElement("div");
  row.className = "date-row";
  row.innerHTML = `
    <label>Excluded date
      <input type="date" class="blocked-date" value="${value || ""}" />
    </label>
    <button type="button" class="btn-icon remove-date" title="Remove date">✕</button>
  `;
  row.querySelector(".remove-date").addEventListener("click", () => row.remove());
  blockedDatesList.appendChild(row);
}

function renderWeekdayChips(active) {
  weekdayGrid.innerHTML = "";
  WEEKDAYS.forEach((day) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "weekday-chip" + (active && active.includes(day) ? " active" : "");
    chip.textContent = day.slice(0, 3);
    chip.dataset.day = day;
    chip.addEventListener("click", () => chip.classList.toggle("active"));
    weekdayGrid.appendChild(chip);
  });
}

document.getElementById("add-range").addEventListener("click", () => createRangeRow());
document.getElementById("add-blocked-date").addEventListener("click", () => createBlockedDateRow());

examClassBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    examClassBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    examClass = Number(btn.dataset.value);
  });
});

// ---------- eligibility preview ----------

function addMonths(date, months) {
  const d = new Date(date.getTime());
  const day = d.getDate();
  d.setMonth(d.getMonth() + months);
  if (d.getDate() !== day) d.setDate(0); // clamp to last day of resulting month
  return d;
}

function updateEligibilityPreview() {
  const raw = form.l_issue_date.value;
  const preview = document.getElementById("eligibility-preview");
  if (!raw) {
    preview.textContent = "Fill in your L issue date to see your earliest eligible test date.";
    return;
  }
  const months = form.completed_driver_training_course.checked ? 9 : 12;
  const eligible = addMonths(new Date(raw + "T00:00:00"), months);
  preview.textContent = `Earliest eligible test date: ${eligible.toISOString().slice(0, 10)} (${months}-month wait)`;
}

form.l_issue_date.addEventListener("input", updateEligibilityPreview);
form.completed_driver_training_course.addEventListener("change", updateEligibilityPreview);

// ---------- detect chat id ----------

document.getElementById("detect-chat-id").addEventListener("click", async () => {
  const btn = document.getElementById("detect-chat-id");
  const token = form.bot_token.value.trim();
  btn.disabled = true;
  btn.textContent = "Detecting…";
  try {
    const res = await fetch("/api/telegram/detect-chat-id", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bot_token: token }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    form.chat_id.value = data.chat_id;
    showStatus(`Chat ID detected: ${data.chat_id}`, "ok");
  } catch (err) {
    showStatus(err.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Detect";
  }
});

// ---------- collect / fill config ----------

function collectConfig() {
  const allowedRanges = [...rangesList.querySelectorAll(".range-row")].map((row) => ({
    start: row.querySelector(".range-start").value || null,
    end: row.querySelector(".range-end").value,
  }));

  const blockedDates = [...blockedDatesList.querySelectorAll(".blocked-date")]
    .map((i) => i.value)
    .filter(Boolean);

  const blockedWeekdays = [...weekdayGrid.querySelectorAll(".weekday-chip.active")].map((c) => c.dataset.day);

  return {
    icbc: {
      last_name: form.last_name.value.trim(),
      licence_number: form.licence_number.value.trim(),
      keyword: form.keyword.value,
      exam_class: examClass,
    },
    licensing: {
      l_issue_date: form.l_issue_date.value,
      completed_driver_training_course: form.completed_driver_training_course.checked,
    },
    location: {
      name: form.location_name.value.trim(),
      a_pos_id: form.a_pos_id.value ? Number(form.a_pos_id.value) : null,
    },
    date_rules: {
      allowed_ranges: allowedRanges,
      blocked_weekdays: blockedWeekdays,
      blocked_dates: blockedDates,
    },
    polling: {
      interval_seconds_min: Number(form.interval_seconds_min.value),
      interval_seconds_max: Number(form.interval_seconds_max.value),
    },
    notifications: {
      telegram: {
        bot_token: form.bot_token.value.trim(),
        chat_id: form.chat_id.value.trim(),
      },
    },
    booking_url: form.booking_url.value.trim(),
  };
}

function fillForm(cfg) {
  form.last_name.value = cfg.icbc?.last_name || "";
  form.licence_number.value = cfg.icbc?.licence_number || "";
  form.keyword.value = cfg.icbc?.keyword || "";
  examClass = cfg.icbc?.exam_class || 7;
  examClassBtns.forEach((b) => b.classList.toggle("active", Number(b.dataset.value) === examClass));

  form.l_issue_date.value = cfg.licensing?.l_issue_date && cfg.licensing.l_issue_date !== "YYYY-MM-DD" ? cfg.licensing.l_issue_date : "";
  form.completed_driver_training_course.checked = !!cfg.licensing?.completed_driver_training_course;

  form.location_name.value = cfg.location?.name || "";
  form.a_pos_id.value = cfg.location?.a_pos_id || "";

  rangesList.innerHTML = "";
  (cfg.date_rules?.allowed_ranges || []).forEach((r) => createRangeRow(r.start, r.end));
  if (!cfg.date_rules?.allowed_ranges?.length) createRangeRow();

  blockedDatesList.innerHTML = "";
  (cfg.date_rules?.blocked_dates || []).forEach((d) => createBlockedDateRow(d));

  renderWeekdayChips(cfg.date_rules?.blocked_weekdays || []);

  form.interval_seconds_min.value = cfg.polling?.interval_seconds_min || 120;
  form.interval_seconds_max.value = cfg.polling?.interval_seconds_max || 300;

  form.bot_token.value = cfg.notifications?.telegram?.bot_token || "";
  form.chat_id.value = cfg.notifications?.telegram?.chat_id || "";

  form.booking_url.value = cfg.booking_url || "https://icbc.com/driver-licensing/visit-dl-office/Book-a-road-test";

  updateEligibilityPreview();
}

// ---------- status / banner helpers ----------

function showStatus(msg, type) {
  const el = document.getElementById("action-status");
  el.textContent = msg;
  el.className = "action-status" + (type ? " " + type : "");
}

function showBanner(msg, type) {
  const el = document.getElementById("banner");
  el.textContent = msg;
  el.className = "banner" + (type ? " " + type : "");
}

// ---------- actions ----------

document.getElementById("btn-save").addEventListener("click", async () => {
  const cfg = collectConfig();
  showStatus("Saving…");
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showStatus("Saved to config.yaml", "ok");
  } catch (err) {
    showStatus(err.message, "err");
  }
});

document.getElementById("btn-test-notify").addEventListener("click", async () => {
  const cfg = collectConfig();
  showStatus("Sending test notification…");
  try {
    const res = await fetch("/api/test-notify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showStatus("Test notification sent — check your phone", "ok");
  } catch (err) {
    showStatus(err.message, "err");
  }
});

document.getElementById("btn-dry-run").addEventListener("click", async () => {
  const cfg = collectConfig();
  const resultsEl = document.getElementById("results");
  showStatus("Checking ICBC…");
  resultsEl.classList.add("hidden");
  try {
    const res = await fetch("/api/dry-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showStatus(`Checked — earliest eligible date ${data.earliest_eligible}`, "ok");
    renderResults(data);
  } catch (err) {
    showStatus(err.message, "err");
  }
});

function renderResults(data) {
  const el = document.getElementById("results");
  el.classList.remove("hidden");
  if (!data.slots.length) {
    el.innerHTML = `<h2>No acceptable slots found right now</h2><p class="hint">Your earliest eligible date is ${data.earliest_eligible}. The tracker will keep checking and notify you the moment something matching your rules opens up.</p>`;
    return;
  }
  const items = data.slots
    .map((s) => `<div class="slot-item"><span>${s.date}</span><span>${s.time}</span></div>`)
    .join("");
  el.innerHTML = `<h2>${data.slots.length} acceptable slot(s) open right now</h2>${items}`;
}

// ---------- pause / resume ----------

const statusText = document.getElementById("status-text");
const togglePauseBtn = document.getElementById("btn-toggle-pause");
let currentlyPaused = false;

function renderStatus() {
  if (currentlyPaused) {
    statusText.textContent = "Paused";
    statusText.className = "status-text paused";
    togglePauseBtn.textContent = "Resume notifications";
  } else {
    statusText.textContent = "Active — checking for openings";
    statusText.className = "status-text active";
    togglePauseBtn.textContent = "Pause notifications";
  }
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    currentlyPaused = !!data.paused;
  } catch (err) {
    // control.json doesn't exist yet - default to active
    currentlyPaused = false;
  }
  renderStatus();
}

togglePauseBtn.addEventListener("click", async () => {
  togglePauseBtn.disabled = true;
  try {
    const res = await fetch(currentlyPaused ? "/api/resume" : "/api/pause", { method: "POST" });
    const data = await res.json();
    currentlyPaused = !!data.paused;
    renderStatus();
  } catch (err) {
    showStatus("Couldn't update pause state: " + err.message, "err");
  } finally {
    togglePauseBtn.disabled = false;
  }
});

// ---------- init ----------

(async function init() {
  renderWeekdayChips([]);
  createRangeRow();
  refreshStatus();

  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    if (data.exists && data.config) {
      fillForm(data.config);
      showBanner("Loaded your existing config.yaml — edit and save to update it.", "info");
    }
  } catch (err) {
    // no existing config yet, that's fine
  }
})();
