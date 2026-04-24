/**
 * research.js — Research Agent logic
 * Simulates an AI agent auto-filling the historical research form
 * and drives the live agent-feed panel in real time.
 */

window.ResearchAgent = (function () {
  const FILL_DELAY_BASE = 130;
  const FILL_JITTER     = 90;
  const TOTAL_FIELDS    = 24;

  // Human-readable label for each field id
  const FIELD_LABELS = {
    speakerName:     "Speaker name",
    speechTitle:     "Speech title",
    speechVersion:   "Speech version",
    speechVariations:"Variations",
    speechLanguage:  "Language spoken",
    speechDialect:   "Dialect / accent",
    speechTranscript:"Transcript source",
    locationCity:    "City",
    locationState:   "State / Province",
    locationCountry: "Country",
    speechDate:      "Event date",
    timePeriod:      "Historical era",
    settingType:     "Indoor / outdoor",
    buildingName:    "Building name",
    roomType:        "Room type",
    roomNotes:       "Room details",
    audienceType:    "Audience arrangement",
    audienceSize:    "Audience size",
    audienceNotes:   "Audience notes",
    speakerPosition: "Speaker position",
    micType:         "Audio / mic type",
    speakerAttire:   "Period attire",
    speakerNotes:    "Staging notes",
    accuracyNotes:   "Accuracy constraints"
  };

  const FIELD_ORDER = Object.keys(FIELD_LABELS);

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ── Live Feed helpers ──────────────────────────────────────────
  let logList   = null;
  let activeItem = null;

  function initFeed() {
    logList = document.getElementById("agentLog");
    if (logList) logList.innerHTML = "";  // clear "Initialising…" placeholder
  }

  function pushLog(fieldId, value, status /* 'active' | 'done' */ ) {
    if (!logList) return;
    const label = FIELD_LABELS[fieldId] || fieldId;
    const truncVal = (value && String(value).length > 36)
      ? String(value).slice(0, 36) + "…"
      : (value || "—");

    if (status === "active") {
      const li = document.createElement("li");
      li.className = "agent-log-item active";
      li.innerHTML = `
        <span class="alg-icon" aria-hidden="true">✏️</span>
        <span class="alg-text">
          <span class="alg-field">${label}</span>
          <span class="alg-val">${truncVal}</span>
        </span>`;
      logList.prepend(li);
      activeItem = li;
    } else if (status === "done" && activeItem) {
      activeItem.className = "agent-log-item done";
      activeItem.querySelector(".alg-icon").textContent = "✓";
    }
  }

  // ── Progress helpers ───────────────────────────────────────────
  function updateProgress(filled) {
    const pct = Math.round((filled / TOTAL_FIELDS) * 100);

    const bar    = document.getElementById("agentProgressBar");
    const pctEl  = document.getElementById("agentPct");
    const numEl  = document.getElementById("agentFieldsDone");
    const confB  = document.getElementById("confBar");
    const confP  = document.getElementById("confPct");

    if (bar)   bar.style.width   = pct + "%";
    if (pctEl) pctEl.textContent = pct + "%";
    if (numEl) numEl.textContent = filled;

    // Confidence climbs slightly faster than completion
    const conf = Math.min(100, Math.round(pct * 1.08));
    if (confB) confB.style.width   = conf + "%";
    if (confP) confP.textContent   = conf + "%";
  }

  // ── Main fill function ─────────────────────────────────────────
  function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value || "";
    el.classList.add("autofilled");
    el.classList.add("field-flash");
    setTimeout(() => el.classList.remove("field-flash"), 600);
    // Auto-expand textareas so all filled content is visible
    if (el.tagName === "TEXTAREA") {
      el.style.height = "1px";
      el.style.height = (el.scrollHeight + 4) + "px";
      el.style.overflowY = "hidden";
    }
  }

  async function fillForm(researchData) {
    const statusEl = document.getElementById("agentStatus");
    const badgeEl  = document.getElementById("agentBadge");

    initFeed();
    updateProgress(0);

    if (statusEl) statusEl.textContent = "Research Agent — Analysing historical records…";
    await sleep(800);

    let filled = 0;
    for (let i = 0; i < FIELD_ORDER.length; i++) {
      const key = FIELD_ORDER[i];
      const val = researchData[key];
      if (val === undefined) {
        filled++;
        updateProgress(filled);
        continue;
      }

      // Show field as active in feed while "typing"
      pushLog(key, val, "active");
      if (statusEl) statusEl.textContent = `Research Agent — Filling "${FIELD_LABELS[key]}"…`;

      await sleep(FILL_DELAY_BASE + Math.random() * FILL_JITTER);

      setFieldValue(key, val);
      pushLog(key, val, "done");

      filled++;
      updateProgress(filled);
    }

    // Accuracy tier radio
    const tier = researchData.accuracyTier || "2";
    const tierRadio = document.querySelector(`input[name="accuracyTier"][value="${tier}"]`);
    if (tierRadio) tierRadio.checked = true;

    // Indoor/outdoor field toggle
    toggleIndoorFields(researchData.settingType === "indoor");

    // Mark complete
    if (statusEl) statusEl.textContent = "Research Agent — Complete ✓  All fields confirmed";
    if (badgeEl)  badgeEl.classList.add("complete");
    updateProgress(TOTAL_FIELDS);

    // Final feed summary entry
    if (logList) {
      const li = document.createElement("li");
      li.className = "agent-log-item done";
      li.style.borderLeftColor = "#c9973d";
      li.innerHTML = `
        <span class="alg-icon" aria-hidden="true">🏆</span>
        <span class="alg-text"><span class="alg-field">Research complete</span>
        <span class="alg-val">All ${TOTAL_FIELDS} fields verified</span></span>`;
      logList.prepend(li);
    }
  }

  function toggleIndoorFields(isIndoor) {
    const buildingGroup = document.getElementById("buildingGroup");
    const roomGroup     = document.getElementById("roomGroup");
    if (buildingGroup) buildingGroup.style.opacity = isIndoor ? "1" : "0.38";
    if (roomGroup)     roomGroup.style.opacity     = isIndoor ? "1" : "0.38";
  }

  return { fillForm, toggleIndoorFields };
})();

