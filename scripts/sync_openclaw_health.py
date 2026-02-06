#!/usr/bin/env python3
"""Publish local health.json to the website.

Source (local):
- /Users/hale/Desktop/openclaw_state/health.json

Outputs (repo):
- /status/health.json
- /zh/status/index.html
- /en/status/index.html

This is a lightweight status page; no secrets.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("/Users/hale/Library/Application Support/openclaw_state/health.json")
REPO = Path(__file__).resolve().parents[1]
OUT_JSON = REPO / "status" / "health.json"
OUT_ZH = REPO / "zh" / "status" / "index.html"
OUT_EN = REPO / "en" / "status" / "index.html"


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def esc(s: str) -> str:
    s = s or ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_health():
    if not SRC.exists():
        return {
            "updatedAt": now_iso(),
            "severity": "unknown",
            "notes": ["health.json missing"],
        }
    return json.loads(SRC.read_text(encoding="utf-8"))


def load_llm_quota() -> dict:
    """Fetch model quota/usage snapshot for status page.

    Uses OpenClaw CLI (read-only). Safe to publish: contains only percentages + reset times.
    """
    try:
        env = dict(**os.environ)
        # The OpenClaw agent auth/profile store lives under /var/root in this setup.
        # This script is often run as `hale` via cron; FORCE HOME here so `openclaw status --usage`
        # can see the correct provider/quota snapshot.
        env["HOME"] = "/var/root"

        p = subprocess.run(
            ["openclaw", "status", "--usage", "--json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        j = json.loads(p.stdout)
        usage = j.get("usage") or {}
        providers = usage.get("providers") or []
        # take the first provider (usually openai-codex)
        if not providers:
            return {"ok": False, "detail": "no providers"}
        pr = providers[0]
        windows = pr.get("windows") or []
        out = {
            "ok": True,
            "provider": pr.get("provider"),
            "displayName": pr.get("displayName"),
            "plan": pr.get("plan"),
            "updatedAt": usage.get("updatedAt"),
            "windows": [],
        }
        for w in windows:
            used = w.get("usedPercent")
            try:
                used_i = int(used)
            except Exception:
                used_i = None
            out["windows"].append(
                {
                    "label": w.get("label"),
                    "usedPercent": used_i,
                    "remainPercent": (None if used_i is None else max(0, 100 - used_i)),
                    "resetAt": w.get("resetAt"),
                }
            )
        return out
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def sev_color(sev: str) -> str:
    return {
        "ok": "#2ecc71",
        "warn": "#f1c40f",
        "crit": "#e74c3c",
        "unknown": "#95a5a6",
    }.get(sev, "#95a5a6")


def render(lang: str, h: dict) -> str:
    is_zh = lang == "zh"
    brand = "一号助理" if is_zh else "Assistant No.1"
    title = "Status · 一号助理" if is_zh else "Status · Assistant No.1"
    subtitle = "机器与子系统健康状态（每小时更新）" if is_zh else "Machine + subsystem health (updated hourly)"

    sev = h.get("severity", "unknown")
    updated = h.get("updatedAt", "")
    host = h.get("host", {})
    systems = h.get("systems", {})
    modules = h.get("modules", {})
    integrations = h.get("integrations", {})
    llm = h.get("llmQuota", {}) or {}
    notes = h.get("notes", []) or []

    def yn(v):
        if v is True:
            return "OK"
        if v is False:
            return "BAD"
        return "-"

    rows_systems = []
    rows_modules = []
    rows_integrations = []  # kept for JSON compatibility; not rendered separately

    # Systems (子系统)
    rows_systems.append(("Self-heal" if not is_zh else "自救系统", yn(systems.get("selfHeal", {}).get("ok")), systems.get("selfHeal", {}).get("detail", "")))
    rows_systems.append(("Logging" if not is_zh else "日志系统", yn(systems.get("logging", {}).get("ok")), systems.get("logging", {}).get("detail", "")))
    rows_systems.append(("Monitoring" if not is_zh else "监控系统", yn(systems.get("monitoring", {}).get("ok")), systems.get("monitoring", {}).get("detail", "")))
    rows_systems.append(("Mail" if not is_zh else "邮件系统", yn(systems.get("mail", {}).get("ok")), systems.get("mail", {}).get("detail", "")))
    rows_systems.append(("Tasks" if not is_zh else "任务系统", yn(systems.get("tasks", {}).get("ok")), systems.get("tasks", {}).get("detail", "")))

    # Key components (重要功能组件)
    rows_modules.append(("VPN/Proxy" if not is_zh else "VPN/代理", yn(modules.get("vpnProxy", {}).get("ok")), modules.get("vpnProxy", {}).get("detail", "")))
    # Merge integrations into key components (用户要求：不单独叫“对接”)
    rows_modules.append(("Gateway" if not is_zh else "Gateway", yn(integrations.get("gateway", {}).get("ok")), integrations.get("gateway", {}).get("url", "")))
    gp = integrations.get("gmailPush", {}) or {}
    # Backward compatible: older schema used {state}
    state = gp.get("trafficState") or gp.get("state") or "-"
    sub_ok = gp.get("subscriptionOk")
    sub_txt = yn(sub_ok) if isinstance(sub_ok, bool) else "-"

    rows_modules.append(("Gmail Push Subscription" if not is_zh else "Gmail Push 订阅", sub_txt, "watch status"))
    rows_modules.append(("Gmail Push Traffic" if not is_zh else "Gmail Push 流量", esc(state), "freshness (soft)"))

    notes_html = "".join([f"<li>{esc(n)}</li>" for n in notes]) or ("<li>none</li>" if not is_zh else "<li>无</li>")

    return """<!doctype html>
<html lang='{html_lang}'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>{title}</title>
  <link rel='stylesheet' href='/assets/style.css' />
  <style>
    .sev-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; background:{sev_color}; margin-right:8px; }}
    .kv {{ display:grid; grid-template-columns:160px 1fr; gap:8px 12px; }}
    .tbl {{ width:100%; border-collapse:collapse; }}
    .tbl td, .tbl th {{ border-bottom:1px solid rgba(255,255,255,0.08); padding:10px 8px; text-align:left; }}
    .mono {{ font-family: Menlo, Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='header'>
      <div class='brand'>
        <div class='logo' aria-hidden='true'></div>
        <div>
          <div class='h1'>{brand} <span class='muted'>/ Status</span></div>
          <div class='sub'>{subtitle}</div>
        </div>
      </div>
      <div class='nav'>
        <a href='/{lang}/'>{home}</a>
        <a href='/logs/'>Logs</a>
        <a href='/{lang}/tasks/'>Tasks</a>
        <a href='/{lang}/status/'>Status</a>
        <a href='/{other_lang}/status/'>{other_lang_label}</a>
      </div>
    </div>

    <div class='grid'>
      <section class='card' style='grid-column:1/-1'>
        <h2 style='margin-top:0'><span class='sev-dot'></span>{overall}: {sev}</h2>
        <div class='body'>
          <div class='kv'>
            <div class='k'>updatedAt</div><div class='mono'>{updated}</div>
            <div class='k'>LLM quota</div><div class='mono'>{llm_quota_line}</div>
            <div class='k'>disk free</div><div class='mono'>{disk_pct}% ({disk_gb} GB)</div>
            <div class='k'>memory</div><div class='mono'>{mem_used} / {mem_total} GB (avail {mem_avail} GB)</div>
            <div class='k'>loadavg</div><div class='mono'>{loadavg} (5m/core: {load_ratio})</div>
            <div class='k'>swap used</div><div class='mono'>{swap} MB</div>
          </div>
        </div>
      </section>

      <section class='card'>
        <h2>{systems_title}</h2>
        <div class='body'>
          <table class='tbl'>
            <thead><tr><th>{name}</th><th>{status}</th><th>{detail}</th></tr></thead>
            <tbody>
              {rows_systems}
            </tbody>
          </table>
        </div>
      </section>

      <section class='card'>
        <h2>{modules_title}</h2>
        <div class='body'>
          <table class='tbl'>
            <thead><tr><th>{name}</th><th>{status}</th><th>{detail}</th></tr></thead>
            <tbody>
              {rows_modules}
            </tbody>
          </table>
        </div>
      </section>

      <section class='card' style='grid-column:1/-1'>
        <h2>{notes_title}</h2>
        <div class='body'><ul>{notes}</ul></div>
      </section>

      <section class='card' style='grid-column:1/-1'>
        <h2>Raw</h2>
        <div class='body mono'><a href='/status/health.json'>/status/health.json</a></div>
      </section>
    </div>

    <div class='footer'>© <span id='y'></span> {brand} · Status</div>
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
        home=("首页" if is_zh else "Home"),
        other_lang=("en" if is_zh else "zh"),
        other_lang_label=("EN" if is_zh else "中文"),
        overall=("总体" if is_zh else "Overall"),
        sev=esc(sev),
        updated=esc(updated),
        disk_pct=esc(str(host.get("diskFreePct", "-"))),
        disk_gb=esc(str(host.get("diskFreeGB", "-"))),
        mem_used=esc(str(host.get("memUsedGB", "-"))),
        mem_avail=esc(str(host.get("memAvailGB", "-"))),
        mem_total=esc(str(host.get("memTotalGB", "-"))),
        loadavg=esc(str(host.get("loadavg", "-"))),
        load_ratio=esc(str(host.get("load5mPerCore", "-"))),
        swap=esc(str(host.get("swapUsedMB", "-"))),
        llm_quota_line=esc(
            "-"
            if not llm.get("ok")
            else " | ".join(
                [
                    (
                        f"{w.get('label')}: {w.get('remainPercent')}% left"
                        if not is_zh
                        else f"{w.get('label')}: 剩余 {w.get('remainPercent')}%"
                    )
                    for w in (llm.get("windows") or [])
                    if w.get("remainPercent") is not None
                ]
            )
        ),
        systems_title=("子系统" if is_zh else "Systems"),
        modules_title=("重要功能组件" if is_zh else "Key components"),
        name=("名称" if is_zh else "Name"),
        status=("状态" if is_zh else "Status"),
        detail=("细节" if is_zh else "Detail"),
        notes_title=("备注" if is_zh else "Notes"),
        notes=notes_html,
        sev_color=sev_color(sev),
        rows_systems="\n".join([f"<tr><td>{esc(a)}</td><td class='mono'>{esc(b)}</td><td class='mono'>{esc(c)}</td></tr>" for a,b,c in rows_systems]),
        rows_modules="\n".join([f"<tr><td>{esc(a)}</td><td class='mono'>{esc(b)}</td><td class='mono'>{esc(c)}</td></tr>" for a,b,c in rows_modules]),
    )


def main():
    h = load_health()
    h["llmQuota"] = load_llm_quota()

    (REPO / "status").mkdir(parents=True, exist_ok=True)
    (REPO / "zh" / "status").mkdir(parents=True, exist_ok=True)
    (REPO / "en" / "status").mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ZH.write_text(render("zh", h), encoding="utf-8")
    OUT_EN.write_text(render("en", h), encoding="utf-8")


if __name__ == "__main__":
    main()
