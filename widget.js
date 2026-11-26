(function () {
  const container = document.getElementById("pulsefeed-jobs-widget");
  if (!container) return;

  const FEED_URL = "https://chukwumaadwuofor-ai.github.io/pulsefeed-engine/jobs.json";
  const HUB_URL = "https://chukwumaadwuofor-ai.github.io/pulsefeed-engine/jobs.html";
  const limit = Math.min(parseInt(container.getAttribute("data-limit") || "6", 10), 15);

  function esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  container.innerHTML = `<div style="font-family:system-ui,-apple-system,sans-serif;padding:14px;border:1px solid #30363d;border-radius:12px;background:#0d1117;color:#f0f6fc;">Loading live remote jobs...</div>`;

  fetch(FEED_URL)
    .then((res) => res.json())
    .then((data) => {
      const jobs = (data.jobs || []).slice(0, limit);
      if (!jobs.length) {
        container.innerHTML = "";
        return;
      }

      const itemsHtml = jobs
        .map(
          (j) => `
          <a href="${esc(j.hub_url || HUB_URL)}" target="_blank" rel="noopener noreferrer"
             style="display:block;text-decoration:none;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px;color:#f0f6fc;">
            <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">${esc(j.source_name)} • ${esc(j.location_or_type)}</div>
            <div style="font-size:14px;font-weight:700;color:#ffffff;margin-bottom:4px;">${esc(j.title)}</div>
            <div style="font-size:12px;color:#3fb950;font-weight:700;">View Details &amp; Apply →</div>
          </a>`
        )
        .join("");

      container.innerHTML = `
        <div style="font-family:system-ui,-apple-system,sans-serif;background:#0d1117;border:1px solid #30363d;border-radius:14px;padding:16px;color:#f0f6fc;max-width:640px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;gap:8px;flex-wrap:wrap;">
            <strong style="font-size:15px;color:#ffffff;">💼 Live Remote Jobs</strong>
            <a href="${HUB_URL}" target="_blank" rel="noopener noreferrer" style="font-size:12px;color:#ff90e8;font-weight:700;text-decoration:none;">More Jobs &amp; Offers ↗</a>
          </div>
          ${itemsHtml}
          <div style="text-align:right;font-size:11px;color:#8b949e;margin-top:4px;">
            Powered by <a href="${HUB_URL}" target="_blank" rel="noopener noreferrer" style="color:#58a6ff;text-decoration:none;">PulseFeed Jobs</a>
          </div>
        </div>
      `;
    })
    .catch(() => {
      container.innerHTML = "";
    });
})();
