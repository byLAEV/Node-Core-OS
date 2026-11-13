(() => {
  "use strict";
  const audio = document.getElementById("audio-player");
  const status = document.getElementById("player-status");
  if (!audio || !status) return;
  audio.addEventListener("play", () => { status.textContent = "PLAYING"; });
  audio.addEventListener("pause", () => { status.textContent = audio.ended ? "PLAYBACK ENDED" : "PAUSED"; });
  audio.addEventListener("ended", () => { status.textContent = "PLAYBACK ENDED"; });
  audio.addEventListener("waiting", () => { status.textContent = "BUFFERING"; });
  audio.addEventListener("error", () => { status.textContent = "SOURCE UNAVAILABLE — OPEN ORIGINAL MP3"; });
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch(() => {});
    });
  }
})();