#!/usr/bin/env python3
"""Sync Desktop openclaw_log into the GitHub Pages repo.

- Source: /Users/hale/Desktop/openclaw_log
- Dest:   <repo>/logs/

Writes:
- logs/INDEX.md
- logs/daily/YYYY-MM-DD.md
- logs/index.html (simple directory page)

No secrets should be copied.
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

SRC = Path("/Users/hale/Desktop/openclaw_log")
REPO = Path(__file__).resolve().parents[1]
DST = REPO / "logs"
DST_DAILY = DST / "daily"


def safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_text(encoding="utf-8", errors="ignore")
    # Basic redaction guardrails
    data = re.sub(r"github_pat_[A-Za-z0-9_]+", "[REDACTED_TOKEN]", data)
    data = re.sub(r"(sk-[A-Za-z0-9]{10,})", "[REDACTED_TOKEN]", data)
    dst.write_text(data, encoding="utf-8")


def build_html_index(index_md: Path, out_html: Path) -> None:
    # Minimal HTML with links; markdown stays in .md files.
    lines = index_md.read_text(encoding="utf-8", errors="ignore").splitlines()
    links = []
    for ln in lines:
        m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]\(([^)]+)\)", ln)
        if m:
            date, href = m.group(1), m.group(2)
            links.append((date, href))

    items = "\n".join([f'<li><a href="{href}">{date}</a></li>' for date, href in links])
    html = f"""<!doctype html>
<html lang=\"en\"><head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>OpenClaw Log</title>
  <link rel=\"stylesheet\" href=\"/assets/style.css\" />
</head><body>
<div class=\"wrap\">
  <div class=\"header\">
    <div class=\"brand\"><div class=\"logo\" aria-hidden=\"true\"></div>
      <div>
        <div class=\"h1\">OpenClaw Log <span class=\"muted\">/ daily notes</span></div>
        <div class=\"sub\">Daily activity log (synced from Desktop)</div>
      </div>
    </div>
    <div class=\"nav\">
      <a href=\"/en/\">Home</a>
      <a href=\"/zh/\">中文</a>
      <a href=\"/logs/\">Logs</a>
      <a href=\"/en/tasks/\">Tasks</a>
      <a href=\"/en/status/\">Status</a>
      <a href=\"https://github.com/halewongai\" target=\"_blank\" rel=\"noreferrer\">GitHub</a>
    </div>
  </div>

  <div class=\"card\" style=\"margin-top:16px;\">
    <h2>Index</h2>
    <div class=\"body\">
      <ul>{items}</ul>
      <p class=\"muted\">Notes are published as Markdown files.</p>
    </div>
  </div>

  <div class=\"footer\">© <span id=\"y\"></span> Assistant No.1</div>
</div>
<script src=\"/assets/site.js\"></script>
</body></html>
"""
    out_html.write_text(html, encoding="utf-8")


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"Source not found: {SRC}")

    DST.mkdir(parents=True, exist_ok=True)
    DST_DAILY.mkdir(parents=True, exist_ok=True)

    # Copy index + all daily files
    idx = SRC / "INDEX.md"
    if idx.exists():
        safe_copy(idx, DST / "INDEX.md")

    daily_src = SRC / "daily"
    if daily_src.exists():
        for p in sorted(daily_src.glob("*.md")):
            safe_copy(p, DST_DAILY / p.name)

    # Build an HTML index for convenient browsing
    if (DST / "INDEX.md").exists():
        build_html_index(DST / "INDEX.md", DST / "index.html")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
