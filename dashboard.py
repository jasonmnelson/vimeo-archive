"""
Vimeo Archive Dashboard
=======================
A live-updating dashboard to track download progress.
Run: python3 dashboard.py
Then open http://localhost:8080 in your browser.
"""

import json
import os
import http.server
import socketserver
from pathlib import Path

PORT = 8090
DOWNLOADS_DIR = "downloads"
MANIFEST_FILE = os.path.join(DOWNLOADS_DIR, "manifest.json")

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vimeo Archive Mission Control</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

  :root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --border: #1e2d4a;
    --text: #e2e8f0;
    --text-dim: #64748b;
    --accent: #3b82f6;
    --accent-glow: rgba(59, 130, 246, 0.3);
    --success: #10b981;
    --success-glow: rgba(16, 185, 129, 0.3);
    --warning: #f59e0b;
    --danger: #ef4444;
    --purple: #8b5cf6;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Animated background grid */
  body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
      linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
  }

  .container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem;
    position: relative;
    z-index: 1;
  }

  /* Header */
  .header {
    text-align: center;
    margin-bottom: 2.5rem;
    position: relative;
  }

  .header::after {
    content: '';
    position: absolute;
    bottom: -1rem;
    left: 50%;
    transform: translateX(-50%);
    width: 200px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
  }

  .badge {
    display: inline-block;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    color: white;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 0.35rem 1rem;
    border-radius: 100px;
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, var(--accent) 50%, var(--purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
    letter-spacing: -0.02em;
  }

  .subtitle {
    color: var(--text-dim);
    font-size: 0.95rem;
    font-weight: 400;
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.25rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.3s;
  }

  .stat-card:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
  }

  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
  }

  .stat-card:nth-child(1)::before { background: linear-gradient(90deg, var(--accent), var(--purple)); }
  .stat-card:nth-child(2)::before { background: var(--success); }
  .stat-card:nth-child(3)::before { background: var(--warning); }
  .stat-card:nth-child(4)::before { background: var(--danger); }

  .stat-icon {
    font-size: 1.5rem;
    margin-bottom: 0.3rem;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
  }

  .stat-card:nth-child(1) .stat-value { color: var(--accent); }
  .stat-card:nth-child(2) .stat-value { color: var(--success); }
  .stat-card:nth-child(3) .stat-value { color: var(--warning); }
  .stat-card:nth-child(4) .stat-value { color: var(--danger); }

  .stat-label {
    font-size: 0.75rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-top: 0.25rem;
  }

  /* Main Progress */
  .progress-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .progress-title {
    font-size: 1rem;
    font-weight: 600;
  }

  .progress-pct {
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--accent);
  }

  .progress-bar-outer {
    background: var(--surface2);
    border-radius: 100px;
    height: 28px;
    overflow: hidden;
    position: relative;
    border: 1px solid var(--border);
  }

  .progress-bar-inner {
    height: 100%;
    border-radius: 100px;
    background: linear-gradient(90deg, var(--accent), var(--purple), var(--success));
    background-size: 200% 100%;
    animation: shimmer 3s ease infinite;
    transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    min-width: 2px;
  }

  .progress-bar-inner::after {
    content: '';
    position: absolute;
    top: 0; right: 0; bottom: 0;
    width: 60px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15));
    border-radius: 0 100px 100px 0;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .progress-detail {
    display: flex;
    justify-content: space-between;
    margin-top: 0.75rem;
    font-size: 0.8rem;
    color: var(--text-dim);
  }

  .eta {
    color: var(--accent);
    font-weight: 600;
  }

  /* Disk usage */
  .disk-bar {
    margin-top: 1rem;
  }

  .disk-bar-outer {
    background: var(--surface2);
    border-radius: 100px;
    height: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
  }

  .disk-bar-inner {
    height: 100%;
    border-radius: 100px;
    background: linear-gradient(90deg, var(--purple), var(--accent));
    transition: width 1s ease;
  }

  /* Activity Feed */
  .activity-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    cursor: pointer;
    user-select: none;
  }

  .section-header h2 {
    font-size: 1rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .section-header .count {
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 0.15rem 0.6rem;
    border-radius: 100px;
    font-size: 0.75rem;
    color: var(--text-dim);
    font-weight: 600;
  }

  .chevron {
    transition: transform 0.3s ease;
    color: var(--text-dim);
    font-size: 1.2rem;
  }

  .chevron.collapsed {
    transform: rotate(-90deg);
  }

  .video-list {
    max-height: 500px;
    overflow-y: auto;
    transition: max-height 0.4s ease;
  }

  .video-list.collapsed {
    max-height: 0;
    overflow: hidden;
  }

  .video-list::-webkit-scrollbar {
    width: 6px;
  }

  .video-list::-webkit-scrollbar-track {
    background: var(--surface2);
    border-radius: 3px;
  }

  .video-list::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
  }

  .video-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    border-radius: 10px;
    transition: background 0.2s;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }

  .video-item:hover {
    background: var(--surface2);
  }

  .video-item:last-child {
    border-bottom: none;
  }

  .video-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .video-status-dot.done { background: var(--success); box-shadow: 0 0 8px var(--success-glow); }
  .video-status-dot.failed { background: var(--danger); }
  .video-status-dot.pending { background: var(--text-dim); }
  .video-status-dot.downloading {
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent-glow);
    animation: pulse 1.5s ease infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(1.3); }
  }

  .video-name {
    flex: 1;
    font-size: 0.85rem;
    font-weight: 400;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .video-link {
    font-size: 0.7rem;
    color: var(--text-dim);
    text-decoration: none;
    opacity: 0;
    transition: opacity 0.2s;
    flex-shrink: 0;
  }

  .video-item:hover .video-link {
    opacity: 1;
  }

  .video-link:hover {
    color: var(--accent);
  }

  /* Live indicator */
  .live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: var(--success);
    border-radius: 50%;
    animation: pulse 2s ease infinite;
    margin-right: 0.4rem;
    vertical-align: middle;
  }

  .auto-refresh {
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  /* Footer */
  .footer {
    text-align: center;
    padding: 2rem 0;
    color: var(--text-dim);
    font-size: 0.8rem;
  }

  .footer a {
    color: var(--accent);
    text-decoration: none;
  }

  .ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
    border: 1px solid rgba(59, 130, 246, 0.2);
    padding: 0.4rem 0.8rem;
    border-radius: 100px;
    font-size: 0.75rem;
    color: var(--accent);
    margin-top: 0.75rem;
  }

  /* Responsive */
  @media (max-width: 640px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    h1 { font-size: 1.6rem; }
    .container { padding: 1rem; }
  }
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <div class="badge">Mission Control</div>
    <h1>Vimeo Archive Download</h1>
    <p class="subtitle">North County Christ the King &mdash; Video Library Preservation</p>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-icon">&#127916;</div>
      <div class="stat-value" id="total">--</div>
      <div class="stat-label">Total Videos</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">&#9989;</div>
      <div class="stat-value" id="done">--</div>
      <div class="stat-label">Downloaded</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">&#9203;</div>
      <div class="stat-value" id="pending">--</div>
      <div class="stat-label">Remaining</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">&#9888;&#65039;</div>
      <div class="stat-value" id="failed">--</div>
      <div class="stat-label">Failed</div>
    </div>
  </div>

  <div class="progress-section">
    <div class="progress-header">
      <div>
        <span class="progress-title">Overall Progress</span>
        <span class="auto-refresh">&nbsp;&nbsp;<span class="live-dot"></span>Auto-refreshing every 10s</span>
      </div>
      <div class="progress-pct" id="pct">0%</div>
    </div>
    <div class="progress-bar-outer">
      <div class="progress-bar-inner" id="progress-bar" style="width: 0%"></div>
    </div>
    <div class="progress-detail">
      <span id="disk-usage">Calculating disk usage...</span>
      <span class="eta" id="eta"></span>
    </div>
    <div class="disk-bar" id="disk-section" style="display:none">
      <div class="disk-bar-outer">
        <div class="disk-bar-inner" id="disk-bar" style="width: 0%"></div>
      </div>
    </div>
  </div>

  <!-- Completed Videos -->
  <div class="activity-section" id="done-section">
    <div class="section-header" onclick="toggleSection('done')">
      <h2>&#9989; Completed <span class="count" id="done-count">0</span></h2>
      <span class="chevron" id="done-chevron">&#9660;</span>
    </div>
    <div class="video-list collapsed" id="done-list"></div>
  </div>

  <!-- Failed Videos -->
  <div class="activity-section" id="failed-section" style="display:none">
    <div class="section-header" onclick="toggleSection('failed')">
      <h2>&#9888;&#65039; Failed <span class="count" id="failed-count">0</span></h2>
      <span class="chevron collapsed" id="failed-chevron">&#9660;</span>
    </div>
    <div class="video-list collapsed" id="failed-list"></div>
  </div>

  <!-- Pending Videos -->
  <div class="activity-section">
    <div class="section-header" onclick="toggleSection('pending')">
      <h2>&#9203; Remaining <span class="count" id="pending-count">0</span></h2>
      <span class="chevron collapsed" id="pending-chevron">&#9660;</span>
    </div>
    <div class="video-list collapsed" id="pending-list"></div>
  </div>

  <div class="footer">
    <div>NCCTK Media Archive Project &bull; 2026</div>
    <div class="ai-badge">
      &#129302; Built with Claude Code &mdash; AI-powered archiving
    </div>
  </div>
</div>

<script>
  let prevDone = 0;
  let prevTime = Date.now();
  let rateHistory = [];

  function toggleSection(name) {
    const list = document.getElementById(name + '-list');
    const chevron = document.getElementById(name + '-chevron');
    list.classList.toggle('collapsed');
    chevron.classList.toggle('collapsed');
  }

  function decodeHTML(str) {
    const el = document.createElement('textarea');
    el.innerHTML = str;
    return el.value;
  }

  async function refresh() {
    try {
      const resp = await fetch('/api/status?' + Date.now());
      const data = await resp.json();

      document.getElementById('total').textContent = data.total;
      document.getElementById('done').textContent = data.done;
      document.getElementById('pending').textContent = data.pending;
      document.getElementById('failed').textContent = data.failed;

      const pct = data.total > 0 ? ((data.done / data.total) * 100) : 0;
      document.getElementById('pct').textContent = pct.toFixed(1) + '%';
      document.getElementById('progress-bar').style.width = pct + '%';

      // Calculate ETA based on download rate
      const now = Date.now();
      if (prevDone > 0 && data.done > prevDone) {
        const elapsed = (now - prevTime) / 1000 / 60; // minutes
        const rate = (data.done - prevDone) / elapsed; // videos per minute
        rateHistory.push(rate);
        if (rateHistory.length > 6) rateHistory.shift();

        const avgRate = rateHistory.reduce((a, b) => a + b, 0) / rateHistory.length;
        const remaining = data.pending + data.failed;
        const etaMin = remaining / avgRate;

        let etaStr;
        if (etaMin < 60) {
          etaStr = Math.round(etaMin) + ' min remaining';
        } else {
          const hrs = Math.floor(etaMin / 60);
          const mins = Math.round(etaMin % 60);
          etaStr = hrs + 'h ' + mins + 'm remaining';
        }
        document.getElementById('eta').textContent = etaStr;
      }
      prevDone = data.done;
      prevTime = now;

      // Disk usage
      if (data.disk_usage_mb) {
        const gb = (data.disk_usage_mb / 1024).toFixed(1);
        document.getElementById('disk-usage').textContent =
          gb + ' GB downloaded (' + data.file_count + ' files)';
      }

      // Render video lists
      renderList('done', data.videos_done, 'done');
      renderList('failed', data.videos_failed, 'failed');
      renderList('pending', data.videos_pending, 'pending');

      document.getElementById('done-count').textContent = data.done;
      document.getElementById('failed-count').textContent = data.failed;
      document.getElementById('pending-count').textContent = data.pending;

      if (data.failed > 0) {
        document.getElementById('failed-section').style.display = 'block';
      }

    } catch (e) {
      console.error('Refresh error:', e);
    }
  }

  function renderList(name, videos, status) {
    const el = document.getElementById(name + '-list');
    if (!videos || videos.length === 0) {
      el.innerHTML = '<div style="padding: 1rem; color: var(--text-dim); font-size: 0.85rem; text-align: center;">None yet</div>';
      return;
    }

    // For done list, show most recent first
    const items = status === 'done' ? [...videos].reverse() : videos;

    el.innerHTML = items.map(v =>
      '<div class="video-item">' +
        '<span class="video-status-dot ' + status + '"></span>' +
        '<span class="video-name">' + decodeHTML(v.name) + '</span>' +
        '<a class="video-link" href="' + v.link + '" target="_blank">view &rarr;</a>' +
      '</div>'
    ).join('');
  }

  // Initial load + auto-refresh
  refresh();
  setInterval(refresh, 10000);
</script>

</body>
</html>"""


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif self.path.startswith('/api/status'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            data = self.get_status()
            self.wfile.write(json.dumps(data).encode())

        else:
            self.send_error(404)

    def get_status(self):
        import re

        try:
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Try backup
            try:
                with open(MANIFEST_FILE + ".bak") as f:
                    manifest = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"total": 0, "done": 0, "pending": 0, "failed": 0,
                        "videos_done": [], "videos_failed": [], "videos_pending": [],
                        "disk_usage_mb": 0, "file_count": 0}

        videos = manifest.get("videos", {})

        # Ground truth: check yt-dlp archive and actual files on disk
        confirmed_ids = set()
        archive_path = os.path.join(DOWNLOADS_DIR, "downloaded.txt")
        if os.path.exists(archive_path):
            with open(archive_path) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        confirmed_ids.add(parts[1])

        dl_path = Path(DOWNLOADS_DIR)
        disk_usage = 0
        file_count = 0
        if dl_path.exists():
            for f in dl_path.glob("*.mp4"):
                disk_usage += f.stat().st_size
                file_count += 1
                match = re.search(r'\[(\d+)\]', f.name)
                if match:
                    confirmed_ids.add(match.group(1))

        done_list = []
        failed_list = []
        pending_list = []

        for vid_id, info in videos.items():
            entry = {"name": info.get("name", "Unknown"), "link": info.get("link", "")}
            # Trust disk over manifest
            if vid_id in confirmed_ids:
                done_list.append(entry)
            elif info["status"] == "failed":
                failed_list.append(entry)
            else:
                pending_list.append(entry)

        return {
            "total": len(videos),
            "done": len(done_list),
            "pending": len(pending_list),
            "failed": len(failed_list),
            "videos_done": done_list,
            "videos_failed": failed_list,
            "videos_pending": pending_list,
            "disk_usage_mb": round(disk_usage / (1024 * 1024), 1),
            "file_count": file_count,
        }

    def log_message(self, format, *args):
        pass  # Suppress request logging


def main():
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Dashboard running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
