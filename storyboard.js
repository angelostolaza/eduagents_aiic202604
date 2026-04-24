/**
 * storyboard.js — Storyboard Agent
 * Generates a sequence of storyboard scenes from speech + research data.
 */

window.StoryboardAgent = (function () {

  // Scene templates based on speech context
  function buildScenes(speech, research, controls) {
    const figure = research.speakerName || speech.figure;
    const title  = research.speechTitle  || speech.speech;
    const venue  = research.locationCity
      ? `${research.locationCity}, ${research.locationCountry}`
      : "Historical venue";
    const isOutdoor = research.settingType !== "indoor";
    const hasMic    = research.micType && research.micType !== "none";
    const perspective = controls.perspective || "audience-pov";
    const colorGrade  = controls.colorGrade  || "cinematic";

    const gradeLabel = { cinematic: "🎬 Cinematic", documentary: "📽 Documentary", neutral: "⚪ Neutral" }[colorGrade] || "🎬 Cinematic";
    const perspLabel = { "audience-pov": "Audience POV", "multi-shot": "Multi-Shot Cinematic" }[perspective] || "Audience POV";

    const scenes = [
      {
        num: 1,
        emoji: "🌅",
        type: "Establishing Shot",
        desc: `Wide ${isOutdoor ? "outdoor" : "interior"} establishing shot — ${venue}. ${research.timePeriod || "Period setting"}.`,
        annotation: `${gradeLabel} · ${perspLabel}`,
        duration: "4s"
      },
      {
        num: 2,
        emoji: "👥",
        type: "Audience Wide",
        desc: `Crowd / audience arrives. ${research.audienceNotes || "Period-accurate crowd fills the space."} ${research.audienceSize ? `(${research.audienceSize})` : ""}`,
        annotation: "Ambient crowd audio, period-accurate dress",
        duration: "5s"
      },
      {
        num: 3,
        emoji: "🚶",
        type: "Figure Entrance",
        desc: `${figure} enters and approaches the ${research.speakerPosition === "podium" ? "podium" : "speaking position"}. Period-accurate attire: ${research.speakerAttire || "historically reconstructed dress"}.`,
        annotation: "Underscored by period-appropriate ambient sound",
        duration: "6s"
      },
      {
        num: 4,
        emoji: "🎙️",
        type: "Opening — Close-Up",
        desc: `Close-up on ${figure}'s face as they begin. ${hasMic ? `${research.micType} microphone visible.` : "No amplification — natural projection."} Lips begin to move.`,
        annotation: `Speech audio begins: "${(research.speechTranscript || "").substring(0, 60)}…"`,
        duration: "8s"
      },
      {
        num: 5,
        emoji: "🎤",
        type: "Delivery — Mid Speech",
        desc: `${perspLabel === "Audience POV" ? "From the audience's point of view" : "Intercutting close-ups and wide"}: ${figure} delivers the central argument with ${research.speakerNotes || "period-authentic delivery style"}.`,
        annotation: "Peak emotional intensity of the speech",
        duration: "12s"
      },
      {
        num: 6,
        emoji: "👁️",
        type: "Reaction Cutaway",
        desc: `Audience reactions — faces in the crowd, eyes locked forward, emotional responses. ${research.audienceNotes || ""}`,
        annotation: "Humanises the moment — history felt, not just heard",
        duration: "5s"
      },
      {
        num: 7,
        emoji: "🔥",
        type: "Climax — Key Line",
        desc: `Tight on ${figure} delivering the most famous line. ${research.speakerNotes ? `Delivery note: ${research.speakerNotes}` : "Full emotional weight."} Camera pushes in slowly.`,
        annotation: `"${getKeyLine(research.speechTranscript)}"`,
        duration: "10s"
      },
      {
        num: 8,
        emoji: "🌄",
        type: "Closing Wide",
        desc: `${figure} finishes. Silence. Crowd reacts — ${isOutdoor ? "sound carries across the open air" : "echo in the chamber"}.`,
        annotation: "Holds on wide to let the moment breathe",
        duration: "6s"
      },
      {
        num: 9,
        emoji: "📜",
        type: "Title Card",
        desc: `Text overlay: "${figure}" and "${title}" · ${research.speechDate || research.timePeriod || ""} · ${venue}`,
        annotation: `${gradeLabel} · Fade to black`,
        duration: "4s"
      }
    ];

    return scenes;
  }

  function getKeyLine(transcript) {
    if (!transcript) return "…";
    // Find a sentence between 40–120 chars that looks like a key statement
    const sentences = transcript.replace(/\n/g, " ").split(/(?<=[.!?])\s+/);
    const candidate = sentences.find(s => s.length > 40 && s.length < 140) || sentences[0];
    return candidate ? candidate.substring(0, 100) + (candidate.length > 100 ? "…" : "") : "…";
  }

  function renderScenes(scenes) {
    const grid = document.getElementById("storyboardGrid");
    if (!grid) return;
    grid.innerHTML = "";

    scenes.forEach((scene, idx) => {
      const card = document.createElement("div");
      card.className = "storyboard-scene";
      card.setAttribute("role", "listitem");
      card.setAttribute("draggable", "true");
      card.dataset.index = idx;

      card.innerHTML = `
        <div class="scene-thumb" style="background: ${thumbColor(scene.type)}">
          <span class="scene-number">${scene.num}</span>
          <span style="font-size:2rem">${scene.emoji}</span>
          <span class="scene-duration">${scene.duration}</span>
        </div>
        <div class="scene-info">
          <div class="scene-type">${scene.type}</div>
          <div class="scene-desc">${scene.desc}</div>
          <div class="scene-annotation">${scene.annotation}</div>
        </div>
      `;

      // Drag-to-reorder
      card.addEventListener("dragstart", onDragStart);
      card.addEventListener("dragover",  onDragOver);
      card.addEventListener("drop",      onDrop);
      card.addEventListener("dragend",   onDragEnd);

      grid.appendChild(card);
    });
  }

  function thumbColor(type) {
    const map = {
      "Establishing Shot": "#1a2a3a",
      "Audience Wide":     "#1a1a2a",
      "Figure Entrance":   "#2a1a1a",
      "Opening — Close-Up":"#2a2a1a",
      "Delivery — Mid Speech": "#1a2a1a",
      "Reaction Cutaway":  "#1a1a2a",
      "Climax — Key Line": "#2a1010",
      "Closing Wide":      "#1a2a2a",
      "Title Card":        "#0d0b08"
    };
    return map[type] || "#1a1a1a";
  }

  // ── Drag-to-reorder ──
  let dragSrc = null;

  function onDragStart(e) {
    dragSrc = this;
    this.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  }

  function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    return false;
  }

  function onDrop(e) {
    e.stopPropagation();
    if (dragSrc !== this) {
      const grid = document.getElementById("storyboardGrid");
      const cards = [...grid.querySelectorAll(".storyboard-scene")];
      const srcIdx  = cards.indexOf(dragSrc);
      const destIdx = cards.indexOf(this);
      if (srcIdx < destIdx) {
        grid.insertBefore(dragSrc, this.nextSibling);
      } else {
        grid.insertBefore(dragSrc, this);
      }
      // Renumber
      [...grid.querySelectorAll(".scene-number")].forEach((el, i) => { el.textContent = i + 1; });
    }
    return false;
  }

  function onDragEnd() {
    this.classList.remove("dragging");
  }

  return { buildScenes, renderScenes };
})();
