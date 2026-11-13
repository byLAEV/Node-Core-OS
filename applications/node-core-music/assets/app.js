(() => {
  "use strict";
  const list = document.getElementById("track-list");
  const count = document.getElementById("track-count");
  if (!list) return;
  const make = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  };
  const renderTrack = (track) => {
    const card = make("article", "track-card");
    const cover = make("div", "cover");
    cover.setAttribute("aria-label", "Minimal cover artwork for " + track.title);
    const coverTitle = make("span", "", track.title);
    const coverSub = make("small", "", track.version ? "VERSION " + track.version : "THE HUMAN LEGACY");
    const coverNo = make("b", "", String(track.sequence).padStart(3, "0"));
    cover.append(coverTitle, coverSub, coverNo);
    const info = make("div", "track-info");
    info.append(make("p", "track-id", track.track_id + " · " + (track.artists || []).join(", ")));
    const title = make("h3", "", track.title + (track.version ? " · " + track.version : ""));
    const credits = make("p", "credits", track.label || "");
    info.append(title, credits);
    const audio = make("audio");
    audio.controls = true;
    audio.preload = "none";
    const source = make("source");
    source.src = track.media.source;
    source.type = track.media.type || "audio/mpeg";
    audio.append(source);
    audio.append(document.createTextNode("Your browser does not support HTML audio."));
    const actions = make("div", "track-actions");
    const link = make("a", "", "Open original MP3 ↗");
    link.href = track.media.source;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const status = make("span", "", "READY TO PLAY");
    status.setAttribute("role", "status");
    audio.addEventListener("play", () => { status.textContent = "PLAYING"; });
    audio.addEventListener("pause", () => { status.textContent = audio.ended ? "PLAYBACK ENDED" : "PAUSED"; });
    audio.addEventListener("ended", () => { status.textContent = "PLAYBACK ENDED"; });
    audio.addEventListener("waiting", () => { status.textContent = "BUFFERING"; });
    audio.addEventListener("error", () => { status.textContent = "SOURCE UNAVAILABLE — OPEN ORIGINAL MP3"; });
    actions.append(link, status);
    info.append(audio, actions);
    card.append(cover, info);
    return card;
  };
  fetch("./catalog/catalog.json")
    .then(response => { if (!response.ok) throw new Error("Catalog request failed"); return response.json(); })
    .then(catalog => {
      const tracks = (catalog.tracks || []).slice().sort((a,b) => a.sequence - b.sequence);
      tracks.forEach(track => list.append(renderTrack(track)));
      if (count) count.textContent = String(tracks.length).padStart(2, "0") + (tracks.length === 1 ? " TRACK" : " TRACKS");
    })
    .catch(() => { list.textContent = "CATALOG UNAVAILABLE — PLEASE RELOAD"; });
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch(() => {});
    });
  }
})();