#!/usr/bin/env python3
"""Sync OpenClaw tasks into the website repo and regenerate Tasks pages.

Source of truth (local): /var/root/.openclaw/state/tasks.json
Outputs (repo):
- /tasks/tasks.json
- /zh/tasks/index.html
- /en/tasks/index.html
"""

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path("/Users/hale/Desktop/openclaw_state/tasks.json")
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR_ZH = REPO_ROOT / "zh" / "tasks"
OUT_DIR_EN = REPO_ROOT / "en" / "tasks"
OUT_JSON = REPO_ROOT / "tasks" / "tasks.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state():
    if not STATE_PATH.exists():
        return {"meta": {"version": 1}, "tasks": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def esc(s: str) -> str:
    s = s or ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_page(lang: str, tasks) -> str:
    is_zh = lang == "zh"
    title = "Tasks · 一号助理" if is_zh else "Tasks · Assistant No.1"
    brand = "一号助理" if is_zh else "Assistant No.1"
    home = "首页" if is_zh else "Home"
    other_lang = "EN" if is_zh else "中文"
    other_href = "/en/tasks/" if is_zh else "/zh/tasks/"
    subtitle = "任务清单（自动沉淀，默认不提醒）" if is_zh else "Task list (persisted automatically; no reminders by default)"
    hint = "入口：Telegram 发『任务：...』或『todo: ...』；默认不提醒，只沉淀到页面。" if is_zh else "Input: send '任务: ...' or 'todo: ...' in Telegram. No reminders by default; tasks are persisted to this page."

    items = []
    for t in tasks:
        status = t.get("status", "open")
        if status not in ("open", "done"):
            status = "open"
        badge = "OPEN" if status == "open" else "DONE"
        text = esc(t.get("text", ""))
        note = esc(t.get("note", ""))
        created = esc(t.get("createdAt", ""))
        due = esc(t.get("dueAt", ""))
        owner = esc(t.get("owner", ""))

        meta_bits = []
        if created:
            meta_bits.append(f"created: {created}")
        if due:
            meta_bits.append(f"due: {due}")
        if owner:
            meta_bits.append(f"owner: {owner}")
        meta_html = " · ".join(meta_bits)

        note_html = f"<div class='task-note'>{note}</div>" if note else ""
        items.append(
            "<li class='task {status}'>"
            "<div class='task-top'><span class='badge'>{badge}</span><span class='task-text'>{text}</span></div>"
            "<div class='task-meta'>{meta}</div>"
            "{note}"
            "</li>".format(status=status, badge=badge, text=text, meta=meta_html, note=note_html)
        )

    list_html = "\n".join(items) if items else ("<div class='muted'>暂无任务</div>" if is_zh else "<div class='muted'>No tasks yet</div>")
    updated = now_iso()

    return """<!doctype html>
<html lang='{html_lang}'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>{title}</title>
  <link rel='stylesheet' href='/assets/style.css' />
  <style>
    .tasks-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; }}
    ul.tasks {{ list-style:none; padding:0; margin:0; }}
    .task {{ padding:14px 14px; border:1px solid rgba(255,255,255,0.08); border-radius:12px; margin-bottom:10px; background:rgba(255,255,255,0.03); }}
    .task.done {{ opacity:0.7; }}
    .task-top {{ display:flex; gap:10px; align-items:flex-start; }}
    .badge {{ font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid rgba(255,255,255,0.18); }}
    .task-text {{ font-size:15px; }}
    .task-meta {{ margin-top:6px; font-size:12px; color:rgba(255,255,255,0.65); }}
    .task-note {{ margin-top:8px; font-size:13px; color:rgba(255,255,255,0.85); white-space:pre-wrap; }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='header'>
      <div class='brand'>
        <div class='logo' aria-hidden='true'></div>
        <div>
          <div class='h1'>{brand} <span class='muted'>/ Tasks</span></div>
          <div class='sub'>{subtitle}</div>
        </div>
      </div>
      <div class='nav'>
        <a href='/{lang}/'>{home}</a>
        <a href='/{lang}/projects/'>Projects</a>
        <a href='/{lang}/research/'>Research</a>
        <a href='/{lang}/automation/'>Automation</a>
        <a href='/{lang}/usage/'>Usage</a>
        <a href='/logs/'>Logs</a>
        <a href='{other_href}'>{other_lang}</a>
      </div>
    </div>

    <div class='grid'>
      <section class='card' style='grid-column:1/-1'>
        <div class='tasks-head'>
          <h2 style='margin:0'>{h2}</h2>
          <div class='muted' style='font-size:12px'>updated: {updated}</div>
        </div>
        <div class='body'>
          <div class='muted' style='margin-bottom:10px'>{hint}</div>
          <ul class='tasks'>{list_html}</ul>
        </div>
      </section>
    </div>

    <div class='footer'>© <span id='y'></span> {brand} · Tasks</div>
  </div>

  <script src='/assets/site.js'></script>
</body>
</html>
""".format(
        html_lang=("zh-CN" if is_zh else "en"),
        title=title,
        brand=brand,
        subtitle=subtitle,
        lang=("zh" if is_zh else "en"),
        home=home,
        other_href=other_href,
        other_lang=other_lang,
        h2=("任务清单" if is_zh else "Task list"),
        updated=updated,
        hint=esc(hint),
        list_html=list_html,
    )


def main():
    state = load_state()
    tasks = state.get("tasks", []) or []
    tasks_sorted = sorted(tasks, key=lambda t: (t.get("createdAt", "")), reverse=True)

    (REPO_ROOT / "tasks").mkdir(parents=True, exist_ok=True)
    OUT_DIR_ZH.mkdir(parents=True, exist_ok=True)
    OUT_DIR_EN.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR_ZH / "index.html").write_text(render_page("zh", tasks_sorted), encoding="utf-8")
    (OUT_DIR_EN / "index.html").write_text(render_page("en", tasks_sorted), encoding="utf-8")


if __name__ == "__main__":
    main()
