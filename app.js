/**
 * app.js — HistoryLive Core Application
 * Manages state, step navigation, seed image simulation, and video render simulation.
 */

(function () {
  "use strict";

  /* ─────────────────────────────────────────
     STATE
  ───────────────────────────────────────── */
  const state = {
    currentStep:    1,
    selectedSpeech: null,
    researchData:   {},
    controls: {
      aspectRatio:  "16:9",
      colorGrade:   "cinematic",
      perspective:  "audience-pov"
    },
    seedRevisions:  0,
    scenes:         []
  };

  /* ─────────────────────────────────────────
     STEP NAVIGATION
  ───────────────────────────────────────── */
  function goToStep(n) {
    const panels  = document.querySelectorAll(".step-panel");
    const navItems = document.querySelectorAll(".step-item");

    panels.forEach(p => p.classList.remove("active"));
    navItems.forEach((item) => {
      item.classList.remove("active");
      if (parseInt(item.dataset.step) < n) item.classList.add("done");
      else                                 item.classList.remove("done");
    });

    const targetPanel = document.getElementById(`step${n}`);
    const targetNav   = document.querySelector(`.step-item[data-step="${n}"]`);
    if (targetPanel) targetPanel.classList.add("active");
    if (targetNav)   targetNav.classList.add("active");

    state.currentStep = n;

    // Hide hero once the user enters the app flow
    const hero = document.getElementById("heroSection");
    if (hero) hero.style.display = "none";

    const appMain = document.getElementById("appMain");
    if (appMain) {
      appMain.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  /* ─────────────────────────────────────────
     TOAST
  ───────────────────────────────────────── */
  let toastTimer;
  function showToast(msg, duration = 3200) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.textContent = msg;
    toast.classList.add("show");
    toastTimer = setTimeout(() => toast.classList.remove("show"), duration);
  }

  /* ─────────────────────────────────────────
     STEP 1 — SPEECH SELECTION
  ───────────────────────────────────────── */
  // initStep1 removed — speech selection is now done via the gallery on the hero section

  function renderSpeechCards(data) {
    const grid = document.getElementById("speechGrid");
    grid.innerHTML = "";
    if (!data.length) {
      grid.innerHTML = `<p class="text-muted" style="grid-column:1/-1;padding:2rem 0;">No speeches match your search.</p>`;
      return;
    }
    data.forEach(s => {
      const card = document.createElement("div");
      card.className = "speech-card";
      card.dataset.era = s.era;
      card.setAttribute("role", "listitem");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", `${s.figure} — ${s.speech}`);
      card.dataset.id = s.id;

      card.innerHTML = `
        <div class="card-select-badge" aria-hidden="true">✓</div>
        <div class="card-era">${eraLabel(s.era)} · ${displayYear(s.year)}</div>
        <div class="card-figure">${s.figure}</div>
        <div class="card-speech">${s.speech}</div>
        <p style="font-size:.82rem;color:var(--text-muted);margin-bottom:var(--space-3);line-height:1.45">${s.description}</p>
        <div class="card-meta">
          <span>📍 ${s.research.locationCity}, ${s.research.locationCountry}</span>
          <span>🌐 ${s.research.speechLanguage}</span>
        </div>
      `;

      card.addEventListener("click", () => selectSpeech(s.id));
      card.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectSpeech(s.id); } });

      grid.appendChild(card);
    });
  }

  function selectSpeech(id) {
    document.querySelectorAll(".speech-card").forEach(c => c.classList.remove("selected"));
    const card = document.querySelector(`.speech-card[data-id="${id}"]`);
    if (card) {
      card.classList.add("selected");
      card.setAttribute("aria-pressed", "true");
    }
    state.selectedSpeech = window.SPEECHES_DB.find(s => s.id === id) || null;
    if (state.selectedSpeech) {
      showToast(`"${state.selectedSpeech.speech}" selected — ${state.selectedSpeech.figure}`);
    }
  }

  function filterCards() {
    const query  = document.getElementById("speechSearch").value.toLowerCase().trim();
    const active = document.querySelector(".filter-btn.active")?.dataset.filter || "all";

    const filtered = window.SPEECHES_DB.filter(s => {
      const matchEra = active === "all" || s.era === active;
      const matchQ   = !query ||
        s.figure.toLowerCase().includes(query) ||
        s.speech.toLowerCase().includes(query) ||
        String(s.year).includes(query) ||
        s.research.locationCity.toLowerCase().includes(query) ||
        s.description.toLowerCase().includes(query);
      return matchEra && matchQ;
    });

    renderSpeechCards(filtered);

    // Re-select if previously selected card is still visible
    if (state.selectedSpeech) {
      const card = document.querySelector(`.speech-card[data-id="${state.selectedSpeech.id}"]`);
      if (card) card.classList.add("selected");
    }
  }

  function eraLabel(era) {
    return {
      ancient: "Ancient", medieval: "Medieval",
      "modern-early": "Early Modern", modern: "Modern",
      contemporary: "Contemporary"
    }[era] || era;
  }

  function displayYear(year) {
    return year < 0 ? `${Math.abs(year)} BCE` : `${year} CE`;
  }

  /* ─────────────────────────────────────────
     STEP 2 — FIGURE PORTRAIT + VIDEO REQUEST
  ───────────────────────────────────────── */

  // Maps figure names to their gallery portrait images
  const FIGURE_IMAGES = {
    "Abraham Lincoln":            "images/Abrahamlincon.png",
    "John F. Kennedy":            "images/John F. Kennedy.png",
    "Dr. Martin Luther King Jr.": "images/Dr. Martin Luther King Jr..png",
    "Hammurabi":                  "images/Hammurabi.png",
    "Sojourner Truth":            "images/Sojourner Truth's.png",
    "Malcolm X":                  "images/MalcolmX.png",
    "Winston Churchill":          "images/Abrahamlincon.png", // fallback
    "Pericles":                   "images/Hammurabi.png",      // fallback
    "Nelson Mandela":             "images/MalcolmX.png"        // fallback
  };

  // All available video files with their figure + title metadata
  const ALL_VIDEOS = [
    { fig: "Abraham Lincoln", title: "Gettysburg Address",  src: "video/gettysburg%20address.mp4" },
    { fig: "John F. Kennedy", title: "Moon Speech",          src: "video/John%20F.%20Kennedy.mp4" },
    { fig: "Hammurabi",       title: "Code of Hammurabi",    src: "video/Hammurabi.mp4" },
    { fig: "Sojourner Truth", title: "Ain't I a Woman?",     src: "video/Sojourner%20Truth's.mp4" },
    { fig: "VozEra",          title: "VozEra Demo",          src: "video/VozEra.mp4" }
  ];

  // Carousel state for the step-2 video spotlight
  const rvState = { items: [], current: 0, timer: null };

  function rvUpdate() {
    const { items, current } = rvState;
    const total = items.length;
    if (!total) return;

    const prev = (current - 1 + total) % total;
    const next = (current + 1) % total;

    items.forEach((item, idx) => {
      const vid = item.querySelector("video");
      item.classList.remove("rv-active", "rv-prev", "rv-next");
      if (idx === current) {
        item.classList.add("rv-active");
        if (vid) { vid.currentTime = 0; vid.play().catch(() => {}); }
      } else if (idx === prev) {
        item.classList.add("rv-prev");
        if (vid) vid.pause();
      } else if (idx === next) {
        item.classList.add("rv-next");
        if (vid) vid.pause();
      } else {
        if (vid) vid.pause();
      }
    });

    const active = items[current];
    const capTitle = document.getElementById("rvCapTitle");
    const capFig   = document.getElementById("rvCapFig");
    if (capTitle) capTitle.textContent = active.dataset.title || "";
    if (capFig)   capFig.textContent   = active.dataset.fig   || "";
  }

  function rvStartTimer() { /* auto-loop disabled — arrows only */ }
  function rvResetTimer() { /* auto-loop disabled — arrows only */ }

  // Build & populate the spotlight carousel, putting figure's video first
  function updateVideoSection(figureName) {
    const spotlight = document.getElementById("rvSpotlight");
    if (!spotlight) return;

    // Reorder: selected figure's video first, then the rest
    const figIdx = ALL_VIDEOS.findIndex(v => v.fig === figureName);
    const ordered = figIdx !== -1
      ? [ALL_VIDEOS[figIdx], ...ALL_VIDEOS.slice(0, figIdx), ...ALL_VIDEOS.slice(figIdx + 1)]
      : ALL_VIDEOS.slice();

    // Clear & rebuild DOM items
    spotlight.innerHTML = "";
    rvState.items = [];
    rvState.current = 0;
    clearInterval(rvState.timer);

    ordered.forEach(v => {
      const item = document.createElement("div");
      item.className   = "rv-item";
      item.dataset.title = v.title;
      item.dataset.fig   = v.fig;

      const vid = document.createElement("video");
      vid.className = "rv-video";
      vid.muted      = true;
      vid.loop       = true;
      vid.playsInline = true;
      const source = document.createElement("source");
      source.src  = v.src;
      source.type = "video/mp4";
      vid.appendChild(source);

      item.appendChild(vid);
      spotlight.appendChild(item);
      rvState.items.push(item);

      // Click on active item — open modal; click on prev/next — navigate
      item.addEventListener("click", () => {
        if (item.classList.contains("rv-active")) {
          const src = v.src;
          const modal     = document.getElementById("rvModal");
          const modalVid  = document.getElementById("rvModalVideo");
          const modalTitle = document.getElementById("rvModalTitle");
          const modalFig   = document.getElementById("rvModalFig");
          if (modal && modalVid) {
            modalVid.src = src;
            if (modalTitle) modalTitle.textContent = v.title;
            if (modalFig)   modalFig.textContent   = v.fig;
            modal.classList.add("is-open");
            modalVid.currentTime = 0;
            modalVid.play().catch(() => {});
          }
        } else {
          rvState.current = rvState.items.indexOf(item);
          rvUpdate();
          rvResetTimer();
        }
      });
    });

    rvUpdate();
    rvStartTimer();

    // Wire arrow buttons (safe to re-attach since we replace listeners)
    const prevBtn = document.getElementById("rvPrev");
    const nextBtn = document.getElementById("rvNext");
    if (prevBtn) {
      const newPrev = prevBtn.cloneNode(true);
      prevBtn.parentNode.replaceChild(newPrev, prevBtn);
      newPrev.addEventListener("click", () => {
        rvState.current = (rvState.current - 1 + rvState.items.length) % rvState.items.length;
        rvUpdate(); rvResetTimer();
      });
    }
    if (nextBtn) {
      const newNext = nextBtn.cloneNode(true);
      nextBtn.parentNode.replaceChild(newNext, nextBtn);
      newNext.addEventListener("click", () => {
        rvState.current = (rvState.current + 1) % rvState.items.length;
        rvUpdate(); rvResetTimer();
      });
    }
  }

  function startResearchAgent() {
    if (!state.selectedSpeech) return;
    const s = state.selectedSpeech;

    // Populate figure portrait panel
    const imgEl  = document.getElementById("riFigureImg");
    const nameEl = document.getElementById("riFigureName");
    const spEl   = document.getElementById("riSpeechTitle");
    const metaEl = document.getElementById("riSpeechMeta");

    if (imgEl) {
      imgEl.src = FIGURE_IMAGES[s.figure] || "images/Abrahamlincon.png";
      imgEl.alt = s.figure;
    }
    if (nameEl) nameEl.textContent = s.figure;
    if (spEl)   spEl.textContent   = s.speech;
    if (metaEl) metaEl.textContent = `${displayYear(s.year)} · ${eraLabel(s.era)}`;

    // Always update prompt to match the selected figure/speech
    const prompt = document.getElementById("videoPrompt");
    if (prompt) {
      prompt.value = `Cinematic portrayal of ${s.figure} delivering the ${s.speech}, ${displayYear(s.year)}.`;
    }

    // Update the sample video section: show selected figure's video first, others below
    updateVideoSection(s.figure);

    // Keep hidden elements in sync for JS compatibility
    const scbFigure = document.getElementById("scbFigure");
    const scbSpeech = document.getElementById("scbSpeech");
    if (scbFigure) scbFigure.textContent = s.figure;
    if (scbSpeech) scbSpeech.textContent = s.speech;
  }

  function initStep2() {
    document.getElementById("step2Back").addEventListener("click", () => {
      resetToStep1();
    });

    document.getElementById("step2Next").addEventListener("click", () => {
      const prompt = document.getElementById("videoPrompt");
      state.videoPrompt = prompt ? prompt.value.trim() : "";
      collectResearchData();
      goToStep(5);
      startVideoRender();
    });

    // Quick-start chips fill the textarea
    document.querySelectorAll(".ri-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const prompt = document.getElementById("videoPrompt");
        if (prompt) prompt.value = chip.dataset.prompt || chip.textContent.trim();
      });
    });
  }

  function collectResearchData() {
    const form   = document.getElementById("researchForm");
    const inputs = form.querySelectorAll("input, select, textarea");
    const data   = {};
    inputs.forEach(el => { if (el.name) data[el.name] = el.value; });
    // Accuracy tier
    const tierChecked = form.querySelector("input[name='accuracyTier']:checked");
    data.accuracyTier = tierChecked ? tierChecked.value : "2";
    state.researchData = data;
  }

  /* ─────────────────────────────────────────
     STEP 3 — SEED IMAGE
  ───────────────────────────────────────── */

  // Curated descriptions for seed image captions per speech id
  const SEED_CAPTIONS = {
    "gettysburg-1863":      "Abraham Lincoln at the Soldiers' National Cemetery, Gettysburg, November 1863. Frock coat, temporary platform, overcast afternoon.",
    "ihaveadream-1963":     "Dr. King at the Lincoln Memorial steps, August 1963. Sunlit crowd of 250,000 stretching toward the Washington Monument.",
    "hammurabi-code":       "Hammurabi in the temple throne room of Babylon, c. 1754 BCE. Oil-lit stone hall, scribes and priests in attendance.",
    "sojourner-truth-1851": "Sojourner Truth at the Women's Rights Convention, Akron, 1851. Church interior, natural window light.",
    "winston-churchill-finest-hour": "Churchill at the dispatch box, House of Commons, June 1940. Wood-panelled chamber, ribbons of cigar smoke.",
    "pericles-funeral-oration":      "Pericles at the Kerameikos cemetery, Athens, 431 BCE. White marble platform, cypress trees, mourning crowd.",
    "jfk-moon-speech":      "President Kennedy at the Rice Stadium podium, Houston, September 1962. Presidential seal, sun-bleached field.",
    "nelson-mandela-release": "Nelson Mandela on the Cape Town City Hall balcony, February 1990. Fist raised, jubilant crowd below in the Grand Parade."
  };

  // Placeholder images (SVG-based generative previews)
  function buildSeedSVG(speech, colorGrade) {
    const colors = {
      cinematic:   ["#1a0d00", "#3d2200", "#c9973d", "#e8c07a"],
      documentary: ["#0a0a0a", "#2a2a2a", "#8a8a8a", "#cccccc"],
      neutral:     ["#0d0f14", "#1a2030", "#4a7ab5", "#8abde0"]
    }[colorGrade] || ["#1a0d00", "#3d2200", "#c9973d", "#e8c07a"];

    const [bg1, bg2, accent1, accent2] = colors;
    const emoji = speech?.emoji || "🎬";

    return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <radialGradient id="bg" cx="40%" cy="50%" r="70%">
      <stop offset="0%" stop-color="${bg2}"/>
      <stop offset="100%" stop-color="${bg1}"/>
    </radialGradient>
    <radialGradient id="spot" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${accent1}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="${accent1}" stop-opacity="0"/>
    </radialGradient>
    <filter id="blur"><feGaussianBlur stdDeviation="30"/></filter>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
      <feBlend in="SourceGraphic" mode="multiply"/>
    </filter>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <ellipse cx="640" cy="360" rx="500" ry="300" fill="url(#spot)" filter="url(#blur)"/>

  <!-- Silhouette figure -->
  <g transform="translate(560, 180)">
    <!-- Head -->
    <ellipse cx="60" cy="30" rx="28" ry="32" fill="${accent1}" opacity="0.85"/>
    <!-- Body -->
    <path d="M20 62 Q60 50 100 62 L110 200 Q60 220 10 200 Z" fill="${accent1}" opacity="0.8"/>
    <!-- Arms -->
    <path d="M20 80 Q0 110 10 140" stroke="${accent1}" stroke-width="14" fill="none" opacity="0.7" stroke-linecap="round"/>
    <path d="M100 80 Q120 110 115 145" stroke="${accent1}" stroke-width="14" fill="none" opacity="0.7" stroke-linecap="round"/>
    <!-- Legs -->
    <rect x="30" y="200" width="22" height="90" rx="8" fill="${accent1}" opacity="0.75"/>
    <rect x="68" y="200" width="22" height="90" rx="8" fill="${accent1}" opacity="0.75"/>
    <!-- Podium -->
    <rect x="-40" y="290" width="200" height="16" rx="4" fill="${accent2}" opacity="0.4"/>
    <rect x="0" y="306" width="120" height="80" rx="4" fill="${accent2}" opacity="0.25"/>
  </g>

  <!-- Crowd silhouettes -->
  ${Array.from({length:18}, (_,i) => {
    const x = 60 + i * 64;
    const y = 560 + (i % 3) * 12;
    const h = 60 + (i % 4) * 8;
    return `<ellipse cx="${x}" cy="${y - h/2}" rx="16" ry="20" fill="${accent1}" opacity="${0.2 + (i%3)*0.07}"/>
            <rect x="${x-8}" y="${y - h/2 + 18}" width="16" height="${h}" rx="5" fill="${accent1}" opacity="${0.15 + (i%4)*0.05}"/>`;
  }).join("")}

  <!-- Atmosphere lines -->
  <line x1="0" y1="0" x2="640" y2="720" stroke="${accent1}" stroke-width="0.5" opacity="0.06"/>
  <line x1="1280" y1="0" x2="640" y2="720" stroke="${accent1}" stroke-width="0.5" opacity="0.06"/>

  <!-- AI watermark label -->
  <rect x="20" y="670" width="280" height="34" rx="5" fill="rgba(0,0,0,0.5)"/>
  <text x="34" y="691" font-family="monospace" font-size="13" fill="${accent2}" opacity="0.9">✦ AI SEED IMAGE — AWAITING APPROVAL</text>

  <!-- Film grain overlay -->
  <rect width="1280" height="720" fill="none" filter="url(#grain)" opacity="0.04"/>
</svg>`)}`;
  }

  function generateSeedImage() {
    const loadingEl = document.getElementById("seedLoading");
    const imgEl     = document.getElementById("seedImage");
    const captionEl = document.getElementById("seedCaption");

    loadingEl.classList.remove("hidden");
    imgEl.classList.add("hidden");

    // Simulate generation delay
    setTimeout(() => {
      const svgSrc = buildSeedSVG(state.selectedSpeech, state.controls.colorGrade);
      imgEl.src = svgSrc;
      imgEl.onload = () => {
        loadingEl.classList.add("hidden");
        imgEl.classList.remove("hidden");
        const cap = SEED_CAPTIONS[state.selectedSpeech?.id] || `${state.selectedSpeech?.figure} — ${state.selectedSpeech?.speech}`;
        captionEl.textContent = `📷 AI-generated seed image: ${cap}`;
        showToast("Seed image generated — review and approve or request revisions.");
      };
      // Fallback if onload doesn't fire (inline SVG)
      setTimeout(() => {
        if (imgEl.classList.contains("hidden")) {
          loadingEl.classList.add("hidden");
          imgEl.classList.remove("hidden");
          captionEl.textContent = SEED_CAPTIONS[state.selectedSpeech?.id] || "";
        }
      }, 200);
    }, 2400);
  }

  function initStep3() {
    // Toggle buttons
    document.querySelectorAll(".toggle-group .toggle-btn").forEach(btn => {
      btn.addEventListener("click", function () {
        const group = this.closest(".toggle-group");
        group.querySelectorAll(".toggle-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-checked", "false");
        });
        this.classList.add("active");
        this.setAttribute("aria-checked", "true");

        const val = this.dataset.value;
        if (["16:9","9:16"].includes(val))             state.controls.aspectRatio = val;
        if (["cinematic","documentary","neutral"].includes(val)) state.controls.colorGrade  = val;
        if (["audience-pov","multi-shot"].includes(val)) state.controls.perspective = val;
      });
    });

    document.getElementById("requestRevision").addEventListener("click", () => {
      state.seedRevisions++;
      const notes = document.getElementById("revisionNotes").value.trim();
      showToast(`Revision ${state.seedRevisions} requested${notes ? ` — "${notes.substring(0,40)}…"` : ""}. Regenerating…`);
      document.getElementById("seedLoading").classList.remove("hidden");
      document.getElementById("seedImage").classList.add("hidden");
      setTimeout(() => {
        generateSeedImageLocal();
        showToast("Revised seed image ready. You can approve or request another revision.");
      }, 1800);
    });

    document.getElementById("approveSeed").addEventListener("click", () => {
      showToast("Seed image approved! Building storyboard…");
      collectResearchData();
      const scenes = StoryboardAgent.buildScenes(
        state.selectedSpeech,
        state.researchData,
        state.controls
      );
      state.scenes = scenes;
      StoryboardAgent.renderScenes(scenes);
      goToStep(4);
    });

    document.getElementById("step3Back").addEventListener("click", () => goToStep(2));
  }

  function generateSeedImageLocal() {
    const imgEl     = document.getElementById("seedImage");
    const loadingEl = document.getElementById("seedLoading");
    const captionEl = document.getElementById("seedCaption");
    const svgSrc = buildSeedSVG(state.selectedSpeech, state.controls.colorGrade);
    imgEl.src = svgSrc;
    loadingEl.classList.add("hidden");
    imgEl.classList.remove("hidden");
    captionEl.textContent = (SEED_CAPTIONS[state.selectedSpeech?.id] || "") +
      (state.seedRevisions > 0 ? ` (Revision ${state.seedRevisions})` : "");
  }

  /* ─────────────────────────────────────────
     STEP 4 — STORYBOARD
  ───────────────────────────────────────── */
  function initStep4() {
    document.getElementById("step4Back").addEventListener("click", () => goToStep(3));
    document.getElementById("step4Next").addEventListener("click", () => {
      goToStep(5);
      startVideoRender();
    });
  }

  /* ─────────────────────────────────────────
     STEP 5 — VIDEO OUTPUT
  ───────────────────────────────────────── */
  const RENDER_STEPS = [
    "Initialising render engine…",
    "Processing historical audio…",
    "Compositing period-accurate scene…",
    "Applying colour grade…",
    "Rendering crowd simulation…",
    "Scoring ambient audio…",
    "Encoding final video…",
    "Optimising output…",
    "Finalising…",
    "Complete ✓"
  ];

  function startVideoRender() {
    // Reset player state for clean re-entry
    const finalVideo = document.getElementById("finalVideo");
    if (finalVideo) {
      finalVideo.pause();
      finalVideo.removeAttribute("src");
      finalVideo.classList.add("hidden");
    }
    const loadingEl = document.getElementById("videoLoading");
    if (loadingEl) {
      loadingEl.classList.remove("hidden");
      const barReset = document.getElementById("renderProgress");
      if (barReset) { barReset.style.width = "0"; barReset.setAttribute("aria-valuenow", 0); }
      const labelReset = document.getElementById("progressLabel");
      if (labelReset) labelReset.textContent = "Starting render engine…";
    }

    populateVideoDetails();
    populateCaptionPanel();

    const bar      = document.getElementById("renderProgress");
    const label    = document.getElementById("progressLabel");
    const loading  = document.getElementById("videoLoading");

    let progress = 0;
    let stepIdx  = 0;

    const interval = setInterval(() => {
      progress += Math.random() * 12 + 4;
      if (progress > 100) progress = 100;

      bar.style.width = `${progress}%`;
      bar.setAttribute("aria-valuenow", Math.round(progress));

      const si = Math.min(Math.floor((progress / 100) * RENDER_STEPS.length), RENDER_STEPS.length - 1);
      if (si !== stepIdx) {
        stepIdx = si;
        label.textContent = RENDER_STEPS[stepIdx];
      }

      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          loading.classList.add("hidden");
          showVideoComplete();
        }, 600);
      }
    }, 320);
  }

  // Map speech IDs to their local video files
  const SPEECH_VIDEOS = {
    "gettysburg-1863":  "video/gettysburg address.mp4",
    "jfk-moon-speech":  "video/jfk.mp4",
    "hammurabi-code":   "video/HammurabiReadingCode.mp4"
  };

  function showVideoComplete() {
    const metaEl   = document.getElementById("videoMeta");
    const loading  = document.getElementById("videoLoading");
    const sp = state.selectedSpeech;

    const videoFile = sp && SPEECH_VIDEOS[sp.id];
    if (videoFile) {
      // Show the real video player
      const finalVideo = document.getElementById("finalVideo");
      loading.classList.add("hidden");
      finalVideo.src = videoFile;
      finalVideo.classList.remove("hidden");
      finalVideo.load();
      finalVideo.play().catch(() => {}); // autoplay may be blocked; controls let user play
    } else {
      // Fallback styled placeholder for speeches without a local video
      const placeholder = document.createElement("div");
      placeholder.style.cssText = `
        width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;
        background:linear-gradient(160deg,rgba(45,31,94,0.9),rgba(19,16,42,0.95));color:var(--accent);gap:12px;border-radius:20px;
      `;
      placeholder.innerHTML = `
        <div style="font-size:4rem">${sp?.emoji || "🎬"}</div>
        <div style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700;color:#E8E4F8;text-align:center;padding:0 2rem">
          ${sp?.figure || "Historical Figure"}
        </div>
        <div style="font-size:.9rem;color:#9B96C0;font-style:italic;text-align:center;padding:0 2rem">
          "${sp?.speech || "Historical Speech"}"
        </div>
        <div style="font-size:.75rem;color:#9B96C0;margin-top:8px">
          ${state.controls.colorGrade.toUpperCase()} · ${state.controls.aspectRatio} · ${
            state.controls.perspective === "audience-pov" ? "Audience POV" : "Multi-Shot Cinematic"
          }
        </div>
        <div style="margin-top:12px;background:rgba(58,191,191,.15);border:1px solid rgba(58,191,191,.3);padding:8px 20px;border-radius:9999px;font-size:.78rem;color:#3ABFBF">
          ✦ Video Ready — Connect AI Video API to render
        </div>
      `;
      loading.replaceWith(placeholder);
    }

    // Populate speech card below video
    const titleEl    = document.getElementById("videoSpeechTitle");
    const subtitleEl = document.getElementById("videoSpeechSubtitle");
    if (titleEl && sp)    titleEl.textContent    = sp.speech || "Historical Speech";
    if (subtitleEl && sp) subtitleEl.textContent = `${sp.figure} · ${displayYear(sp.year)}`;

    // Simulate segment playback on seg bar
    simulateSegBar();

    metaEl.textContent = `${state.controls.aspectRatio} · ${state.controls.colorGrade} grade · ${state.controls.perspective === "audience-pov" ? "Audience POV" : "Multi-Shot"} · Accuracy Tier ${state.researchData.accuracyTier || 2}`;
    showToast("🎬 Your video is ready!");
  }

  function simulateSegBar() {
    const segs = document.querySelectorAll("#videoSegBar .video-seg");
    const indicator = document.getElementById("videoSegIndicator");
    if (!segs.length) return;
    let current = 0;
    function advanceSeg() {
      segs.forEach((s, i) => {
        s.classList.remove("active", "done");
        if (i < current)  s.classList.add("done");
        if (i === current) s.classList.add("active");
      });
      if (indicator) indicator.textContent = `Segment ${current + 1} of ${segs.length}`;
      current++;
      if (current < segs.length) setTimeout(advanceSeg, 2600);
      else {
        segs.forEach(s => { s.classList.remove("active"); s.classList.add("done"); });
        if (indicator) indicator.textContent = `All ${segs.length} segments played`;
      }
    }
    setTimeout(advanceSeg, 300);
  }

  function populateVideoDetails() {
    const dl = document.getElementById("videoDetailsList");
    const r  = state.researchData;
    const s  = state.selectedSpeech;
    if (!dl || !s) return;

    dl.innerHTML = [
      ["Speaker",  r.speakerName  || s.figure],
      ["Speech",   r.speechTitle  || s.speech],
      ["Date",     r.speechDate   || String(s.year)],
      ["Location", [r.locationCity, r.locationState, r.locationCountry].filter(Boolean).join(", ")],
      ["Language", r.speechLanguage || "—"],
      ["Accuracy", `Tier ${r.accuracyTier || 2}`],
      ["Aspect",   state.controls.aspectRatio],
      ["Look",     state.controls.colorGrade],
      ["Camera",   state.controls.perspective === "audience-pov" ? "Audience POV" : "Multi-Shot"]
    ].map(([dt, dd]) => `<dt>${dt}</dt><dd>${dd || "—"}</dd>`).join("");
  }

  function populateCaptionPanel() {
    const panel = document.getElementById("captionPanel");
    const r     = state.researchData;
    if (!panel) return;
    const text = r.speechTranscript?.trim();
    if (text) {
      panel.innerHTML = text.replace(/\n/g, "<br/><br/>");
    } else {
      panel.textContent = "No transcript available for this speech. Historical reconstruction only.";
    }
  }

  /* ─────────────────────────────────────────
     STEP 5 — VIDEO OUTPUT
  ───────────────────────────────────────── */
  function initStep5() {
    document.getElementById("step5Back").addEventListener("click", () => goToStep(2));
    document.getElementById("step5Next").addEventListener("click", () => {
      goToStep(6);
      startActivity();
    });

    document.getElementById("downloadVideo").addEventListener("click", () => {
      showToast("⬇ In production, this would download your generated video file.");
    });

    document.getElementById("shareVideo").addEventListener("click", () => {
      const url = `${window.location.origin}${window.location.pathname}?speech=${state.selectedSpeech?.id || ""}`;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url)
          .then(() => showToast("✓ Share link copied to clipboard!"))
          .catch(() => showToast("↗ Share link: " + url));
      } else {
        showToast("↗ Share link ready (copy from address bar).");
      }
    });

    document.getElementById("startOver").addEventListener("click", resetToStep1);
  }

  /* ─────────────────────────────────────────
     MODAL
  ───────────────────────────────────────── */
  function initModal() {
    const overlay = document.getElementById("modalOverlay");
    const closeBtn = document.getElementById("modalClose");
    if (!overlay || !closeBtn) return;

    closeBtn.addEventListener("click", () => {
      overlay.hidden = true;
    });
    overlay.addEventListener("click", e => {
      if (e.target === overlay) overlay.hidden = true;
    });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && !overlay.hidden) overlay.hidden = true;
    });

    // ── Video spotlight modal (rv-modal) ──
    const rvModal    = document.getElementById("rvModal");
    const rvCloseBtn = document.getElementById("rvModalClose");
    const rvModalVid = document.getElementById("rvModalVideo");

    function closeRvModal() {
      if (!rvModal) return;
      rvModal.classList.remove("is-open");
      if (rvModalVid) { rvModalVid.pause(); rvModalVid.src = ""; }
    }

    if (rvCloseBtn) rvCloseBtn.addEventListener("click", closeRvModal);
    if (rvModal)    rvModal.addEventListener("click", e => { if (e.target === rvModal) closeRvModal(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && rvModal && rvModal.classList.contains("is-open")) closeRvModal();
    });
  }

  /* ─────────────────────────────────────────
     FOOTER YEAR
  ───────────────────────────────────────── */
  const yearEl = document.getElementById("footerYear");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ─────────────────────────────────────────
     CANVAS PARTICLES
  ───────────────────────────────────────── */
  function initHeroCanvas() {
    const canvas = document.getElementById("heroCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let particles = [];

    function resize() {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    function rand(a, b) { return a + Math.random() * (b - a); }

    function spawn() {
      return {
        x:  rand(0, canvas.width),
        y:  rand(canvas.height * 0.1, canvas.height),
        r:  rand(0.4, 2.0),
        vx: rand(-0.1, 0.1),
        vy: rand(-0.5, -0.12),
        a:  rand(0.18, 0.72),
        da: rand(0.0007, 0.0028)
      };
    }

    for (let i = 0; i < 95; i++) {
      const p = spawn();
      p.y = rand(0, canvas.height);
      particles.push(p);
    }

    (function tick() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx; p.y += p.vy; p.a -= p.da;
        if (p.a <= 0 || p.y < -8) {
          particles[i] = spawn();
          particles[i].y = canvas.height + 4;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, 6.2832);
        ctx.fillStyle = `rgba(58,191,191,${p.a})`;
        ctx.fill();
      }
      requestAnimationFrame(tick);
    })();
  }

  /* ─────────────────────────────────────────
     COUNTER ANIMATION
  ───────────────────────────────────────── */
  function animateCounters() {
    document.querySelectorAll(".stat-num[data-target]").forEach(el => {
      const target   = parseInt(el.dataset.target, 10);
      const suffix   = el.dataset.suffix || "";
      const duration = target > 100 ? 1800 : 900;
      let start = null;
      (function step(ts) {
        if (!start) start = ts;
        const pct = Math.min((ts - start) / duration, 1);
        el.textContent = Math.round((1 - Math.pow(1 - pct, 3)) * target) + suffix;
        if (pct < 1) requestAnimationFrame(step);
        else el.textContent = target + suffix;
      })(performance.now());
    });
  }

  /* ─────────────────────────────────────────
     SCROLL REVEAL
  ───────────────────────────────────────── */
  function initScrollReveal() {
    const els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      els.forEach(el => el.classList.add("revealed"));
      animateCounters();
      return;
    }
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add("revealed"); obs.unobserve(e.target); }
      });
    }, { threshold: 0.08 });
    els.forEach(el => obs.observe(el));

    // Counter fires when stats row is in view
    const statsRow = document.querySelector(".hero-stats-row");
    if (statsRow) {
      const cObs = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) { animateCounters(); cObs.disconnect(); }
      }, { threshold: 0.4 });
      cObs.observe(statsRow);
    }
  }

  /* ─────────────────────────────────────────
     DEMO MODE
  ───────────────────────────────────────── */
  const DEMO_ID = "gettysburg-1863";

  function initDemoMode() {
    const overlay = document.createElement("div");
    overlay.id = "demoOverlay";
    overlay.className = "demo-overlay";
    overlay.innerHTML = `
      <span aria-hidden="true">🎬</span>
      <span>Demo — <strong id="demoStepLabel">Starting…</strong></span>
      <button id="stopDemoBtn" aria-label="Stop demo">✕ Stop</button>
    `;
    document.body.appendChild(overlay);

    function setLabel(t) {
      const el = document.getElementById("demoStepLabel");
      if (el) el.textContent = t;
    }

    function runDemo() {
      overlay.classList.add("active");
      setLabel("Step 1 — Selecting speech…");
      setTimeout(() => {
        selectSpeech(DEMO_ID);
        const card = document.querySelector(`.speech-card[data-id="${DEMO_ID}"]`);
        if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 500);
      setTimeout(() => {
        setLabel("Step 2 — Research Agent filling form…");
        goToStep(2); startResearchAgent();
      }, 2000);
      setTimeout(() => {
        setLabel("Step 3 — Generating seed image…");
        collectResearchData(); goToStep(3); generateSeedImage();
      }, 7200);
      setTimeout(() => {
        setLabel("Step 4 — Building storyboard…");
        collectResearchData();
        const scenes = StoryboardAgent.buildScenes(state.selectedSpeech, state.researchData, state.controls);
        state.scenes = scenes;
        StoryboardAgent.renderScenes(scenes);
        goToStep(4);
      }, 11200);
      setTimeout(() => {
        setLabel("Step 5 — Rendering final video…");
        goToStep(5); startVideoRender();
      }, 14800);
      setTimeout(() => {
        setLabel("Demo complete ✓");
        setTimeout(() => overlay.classList.remove("active"), 2800);
      }, 21000);
    }

    document.getElementById("demoModeBtn")?.addEventListener("click", runDemo);
    document.getElementById("heroDemoBtn")?.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      setTimeout(runDemo, 350);
    });
    document.getElementById("stopDemoBtn")?.addEventListener("click", () => {
      overlay.classList.remove("active");
      goToStep(1);
      showToast("Demo stopped. Select a speech to continue.");
    });
    // Keyboard shortcut: D key starts demo
    document.addEventListener("keydown", e => {
      if (e.key !== "d" || e.ctrlKey || e.metaKey || e.altKey) return;
      const active = document.activeElement;
      if (active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA" || active.tagName === "SELECT")) return;
      runDemo();
    });
  }

  /* ─────────────────────────────────────────
     RESET
  ───────────────────────────────────────── */
  function resetToStep1() {
    state.selectedSpeech  = null;
    state.researchData    = {};
    state.seedRevisions   = 0;
    state.scenes          = [];
    state.activityScore   = { correct: 0, streak: 0, best: 0, times: [] };

    // Hide all step panels and nav states
    document.querySelectorAll(".step-panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".step-item").forEach(item => item.classList.remove("active", "done"));

    // Show the hero/gallery again
    const hero = document.getElementById("heroSection");
    if (hero) hero.style.display = "";

    const loadingEl = document.getElementById("seedLoading");
    const imgEl     = document.getElementById("seedImage");
    if (loadingEl) loadingEl.classList.remove("hidden");
    if (imgEl)     imgEl.classList.add("hidden");

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* ─────────────────────────────────────────
     STEP 6 — INTERACTIVE ACTIVITY
  ───────────────────────────────────────── */

  // Activity questions — all multiple choice
  const ACTIVITIES = {
    "gettysburg-1863": [
      { question: "Which war was the backdrop for the Gettysburg Address?", correct: "A",
        options: ["American Civil War", "War of 1812", "Mexican–American War", "World War I"] },
      { question: "Where was the Gettysburg Address delivered?", correct: "B",
        options: ["On the Gettysburg battlefield", "At the Soldiers' National Cemetery dedication", "In the U.S. Capitol", "At the White House"],
        explanation: "Lincoln spoke at the dedication of the Soldiers' National Cemetery, four and a half months after the battle." },
      { question: "Complete the opening: 'Four score and _____ years ago…'", correct: "C",
        options: ["Twenty", "Forty", "Seven", "Ten"],
        explanation: "Four score and seven = 87 years, counting back from 1863 to 1776." },
      { question: "What closing phrase from the Address became a global definition of democracy?", correct: "D",
        options: ["'A new birth of freedom'", "'These dead shall not have died in vain'", "'All men are created equal'", "'Government of the people, by the people, for the people'"] }
    ],
    "ihaveadream-1963": [
      { question: "Where was the 'I Have a Dream' speech delivered?", correct: "B",
        options: ["Capitol Building", "Lincoln Memorial", "White House lawn", "National Mall stage"] },
      { question: "Who called out to Dr. King, prompting him to improvise the 'I Have a Dream' passage?", correct: "C",
        options: ["Aretha Franklin", "Rosa Parks", "Mahalia Jackson", "Coretta Scott King"],
        explanation: "Mahalia Jackson shouted 'Tell them about the dream!' and Dr. King set aside his prepared text." },
      { question: "What was the official name of the march this speech headlined?", correct: "A",
        options: ["March on Washington for Jobs and Freedom", "Selma to Montgomery March", "Chicago Freedom Movement March", "Poor People's Campaign March"] },
      { question: "In what year was the 'I Have a Dream' speech delivered?", correct: "B",
        options: ["1955", "1963", "1968", "1960"] }
    ]
  };

  const GENERIC_ACTIVITIES = [
    { question: "What is the primary purpose of a historically significant speech?", correct: "A",
      options: ["To persuade or inspire an audience toward a shared goal", "To entertain listeners with stories", "To demonstrate the speaker's vocabulary", "To summarise recent news events"] },
    { question: "What term describes documents created at the time of an event by participants?", correct: "B",
      options: ["Secondary sources", "Primary sources", "Tertiary sources", "Archival summaries"] },
    { question: "What term describes the historical period in which a speech was delivered?", correct: "C",
      options: ["Genre", "Narrative", "Era", "Chronicle"],
      explanation: "An 'era' refers to a distinct period of history with defining characteristics." },
    { question: "Which rhetorical device repeats a phrase at the start of successive clauses?", correct: "A",
      options: ["Anaphora", "Metaphor", "Hyperbole", "Alliteration"] }
  ];

  const actState = {
    questions:  [],
    current:    0,
    answered:   false,
    score:      0,
    streak:     0,
    bestStreak: 0,
    times:      [],
    qStart:     0
  };

  function startActivity() {
    const id = state.selectedSpeech?.id;
    actState.questions  = (ACTIVITIES[id] || GENERIC_ACTIVITIES).slice();
    actState.current    = 0;
    actState.answered   = false;
    actState.score      = 0;
    actState.streak     = 0;
    actState.bestStreak = 0;
    actState.times      = [];
    showActivityQuestion();
  }

  function showActivityQuestion() {
    const q = actState.questions[actState.current];
    if (!q) { finishActivity(); return; }
    actState.answered = false;
    actState.qStart   = Date.now();

    // Reset feedback
    document.getElementById("activityFeedback").className = "activity-feedback";

    // Update progress
    document.getElementById("activityProgress").textContent =
      `Question ${actState.current + 1} of ${actState.questions.length}`;

    // Hide next button
    document.getElementById("activityNext").hidden = true;

    // Set question text
    document.getElementById("activityQuestion").textContent = q.question;

    // Populate answer buttons
    const container = document.getElementById("mcContainer");
    const letters = ["A","B","C","D"];
    letters.forEach((l, i) => {
      const btn  = container.querySelector(`[data-letter="${l}"]`);
      const text = container.querySelector(`#mc${l}`);
      text.textContent = q.options[i] || "";
      btn.classList.remove("selected","correct","incorrect");
      btn.setAttribute("aria-pressed","false");
      btn.disabled = false;
      btn.onclick = () => answerQuestion(l, q.correct, q.explanation);
    });
  }

  function answerQuestion(chosen, correct, explanation) {
    if (actState.answered) return;
    actState.answered = true;
    const elapsed = ((Date.now() - actState.qStart) / 1000).toFixed(1);
    actState.times.push(parseFloat(elapsed));

    document.querySelectorAll(".mc-block").forEach(btn => {
      btn.disabled = true;
      const l = btn.dataset.letter;
      if (l === correct) btn.classList.add("correct");
      else if (l === chosen && chosen !== correct) btn.classList.add("incorrect");
    });

    if (chosen === correct) {
      actState.score++;
      actState.streak++;
      actState.bestStreak = Math.max(actState.bestStreak, actState.streak);
      showFeedback("correct", "✓", "Correct!", explanation || "");
    } else {
      actState.streak = 0;
      showFeedback("incorrect", "✗", `Incorrect. The answer was ${correct}.`, explanation || "");
    }
    document.getElementById("activityNext").hidden = false;
  }

  function showFeedback(type, icon, main, explanation) {
    const fb   = document.getElementById("activityFeedback");
    const fbI  = document.getElementById("feedbackIcon");
    const fbM  = document.getElementById("feedbackMain");
    const fbE  = document.getElementById("feedbackExplanation");
    fb.className = `activity-feedback ${type} show`;
    fbI.textContent = icon;
    fbM.textContent = main;
    fbE.textContent = explanation;
  }

  function finishActivity() {
    goToStep(7);
    buildSummary();
  }

  function initStep6() {
    document.getElementById("step6Back").addEventListener("click", () => goToStep(5));
    document.getElementById("activityNext").addEventListener("click", () => {
      actState.current++;
      showActivityQuestion();
    });
  }

  /* ─────────────────────────────────────────
     STEP 7 — END OF SPEECH SUMMARY
  ───────────────────────────────────────── */

  const SPEECH_KEY_POINTS = {
    "gettysburg-1863": [
      "Lincoln invoked the founding principle that 'all men are created equal' to reframe the Civil War as a fight for equality.",
      "The speech redefined the purpose of the war from preserving the Union to ending slavery.",
      "At only 272 words, it remains one of the most quoted speeches in American history.",
      "Lincoln honoured the soldiers' sacrifice by arguing their deaths had consecrated the ground more than any words could.",
      "The closing phrase 'government of the people, by the people, for the people' became a global definition of democracy."
    ],
    "ihaveadream-1963": [
      "Dr. King drew on the Declaration of Independence, describing it as a 'promissory note' to all Americans.",
      "The improvisational 'dream' section was sparked by Mahalia Jackson calling out from the crowd.",
      "The speech directly contributed to the passage of the Civil Rights Act of 1964.",
      "King used the rhetorical device of anaphora — repetition of 'I have a dream' — for maximum emotional impact.",
      "The speech called for racial justice not through violence, but through 'soul force'."
    ]
  };

  const GENERIC_KEY_POINTS = [
    "Historical speeches reflect the values, fears, and aspirations of their era.",
    "Rhetoric — the art of persuasion — has shaped political outcomes across centuries.",
    "Primary sources like speeches give us direct insight into how historical figures communicated.",
    "Context is critical: understanding the audience and occasion transforms how we interpret a speech.",
    "Great speeches often combine emotional appeal, logical argument, and ethical credibility."
  ];

  const SEGMENT_TITLES = [
    "Opening & Context", "Central Argument", "Evidence & Examples",
    "Emotional Appeal", "Closing & Call to Action"
  ];

  function buildSummary() {
    const sp   = state.selectedSpeech;
    const total = actState.questions.length;

    // Score card
    document.getElementById("scoreFinal").textContent  = actState.score;
    document.getElementById("scoreCorrect").textContent = actState.score;
    document.getElementById("scoreStreak").textContent  = actState.bestStreak;
    const avgTime = actState.times.length
      ? (actState.times.reduce((a,b)=>a+b,0) / actState.times.length).toFixed(1) + "s"
      : "—";
    document.getElementById("scoreTime").textContent = avgTime;

    // Denominator
    const denomEl = document.querySelector("#scoreCard .score-denom");
    if (denomEl) denomEl.textContent = `/${total}`;

    // Summary hero
    if (sp) {
      document.getElementById("summaryEmoji").textContent    = sp.emoji || "🎬";
      document.getElementById("step7Title2").textContent     = `${sp.figure} — Done!`;
      document.getElementById("summarySubtitle").textContent = `"${sp.speech}" · ${displayYear(sp.year)}`;
    }

    // Key points
    const points = SPEECH_KEY_POINTS[sp?.id] || GENERIC_KEY_POINTS;
    const kpList = document.getElementById("keyPointsList");
    kpList.innerHTML = points.map((pt, i) => `
      <li class="key-point-item">
        <span class="key-point-num" aria-hidden="true">${i + 1}</span>
        <span>${pt}</span>
      </li>
    `).join("");

    // Replay segments
    const replayGrid = document.getElementById("replayGrid");
    replayGrid.innerHTML = SEGMENT_TITLES.map((title, i) => `
      <button class="replay-seg-btn" aria-label="Replay segment ${i+1}: ${title}" role="listitem">
        <span class="replay-seg-num">Segment ${i + 1}</span>
        <span class="replay-seg-title">${title}</span>
        <span class="replay-seg-dur">~${30 + i * 10}s</span>
        <span class="replay-icon" aria-hidden="true">▶</span>
      </button>
    `).join("");

    replayGrid.querySelectorAll(".replay-seg-btn").forEach((btn, i) => {
      btn.addEventListener("click", () => {
        showToast(`▶ Replaying: Segment ${i+1} — ${SEGMENT_TITLES[i]}`);
      });
    });

    // Side details
    const r  = state.researchData;
    const dl = document.getElementById("summaryDetailsList");
    if (dl && sp) {
      dl.innerHTML = [
        ["Speaker",  r.speakerName  || sp.figure],
        ["Speech",   r.speechTitle  || sp.speech],
        ["Date",     r.speechDate   || displayYear(sp.year)],
        ["Location", [r.locationCity, r.locationCountry].filter(Boolean).join(", ") || "—"],
        ["Score",    `${actState.score} / ${total}`]
      ].map(([dt,dd]) => `<dt>${dt}</dt><dd>${dd || "—"}</dd>`).join("");
    }
  }

  function initStep7() {
    document.getElementById("step7Back").addEventListener("click", () => goToStep(6));
    document.getElementById("step7Restart").addEventListener("click", resetToStep1);
    document.getElementById("tryAnotherSpeech").addEventListener("click", resetToStep1);
    document.getElementById("downloadSummary").addEventListener("click", () => {
      showToast("⬇ In production, this would download a PDF summary.");
    });
    document.getElementById("shareResult").addEventListener("click", () => {
      const sp    = state.selectedSpeech;
      const total = actState.questions.length;
      const text  = `I scored ${actState.score}/${total} on the HistoryLive activity for "${sp?.speech}" — ${sp?.figure}! historyLive.app`;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => showToast("✓ Share text copied!"));
      } else {
        showToast("↗ Share: " + text);
      }
    });
  }

  /* ─────────────────────────────────────────
     INIT
  ───────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    initStep2();
    initStep3();
    initStep4();
    initStep5();
    initStep6();
    initStep7();
    initModal();
    initDemoMode();
    initHeroCanvas();
    initScrollReveal();
    // No goToStep call — hero is visible by default; flow starts when gallery image is clicked

    // Expose for gallery image click-to-research
    window.__appSelectAndResearch = function (speechId) {
      if (!window.SPEECHES_DB.find(s => s.id === speechId)) return;
      selectSpeech(speechId);
      goToStep(2);
      startResearchAgent();
    };
  });

})();
