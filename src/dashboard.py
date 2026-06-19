import html


def render_dashboard(settings_info: dict, stats: dict, recent_emails: list, recent_runs: list) -> str:
    def esc(value) -> str:
        return html.escape(str(value or ""))

    email_rows = ""
    if recent_emails:
        for item in recent_emails:
            badge = "alert" if item.get("is_interesting") else "skip"
            label = "Alert" if item.get("is_interesting") else "Skipped"
            email_rows += f"""
            <tr>
                <td><span class="badge {badge}">{label}</span></td>
                <td>{esc(item.get('subject'))}</td>
                <td>{esc(item.get('sender'))}</td>
                <td>{esc(item.get('category'))}</td>
                <td>{esc(item.get('reason'))}</td>
                <td>{esc(item.get('processed_at'))}</td>
            </tr>"""
    else:
        email_rows = '<tr><td colspan="6" class="empty">No emails processed yet. Run a check to get started.</td></tr>'

    run_rows = ""
    if recent_runs:
        for run in recent_runs:
            status = run.get("status", "unknown")
            status_class = "ok" if status == "success" else "bad"
            run_rows += f"""
            <tr>
                <td>{esc(run.get('started_at'))}</td>
                <td>{esc(run.get('emails_found'))}</td>
                <td>{esc(run.get('emails_processed'))}</td>
                <td>{esc(run.get('alerts_sent'))}</td>
                <td><span class="badge {status_class}">{esc(status)}</span></td>
            </tr>"""
    else:
        run_rows = '<tr><td colspan="5" class="empty">No check runs yet.</td></tr>'

    last_run = stats.get("last_run") or {}
    last_run_text = last_run.get("finished_at") or last_run.get("started_at") or "Never"
    last_run_status = last_run.get("status") or "waiting"
    trigger_url = settings_info.get("trigger_url", "")

    run_button = """
        <button class="btn" id="runBtn" onclick="runCheck()">Run Check Now</button>
        <p id="runStatus" class="hint"></p>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mail Checker Agent</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a2332;
      --panel-2: #243044;
      --text: #e7eef8;
      --muted: #93a4bb;
      --accent: #4f8cff;
      --green: #34d399;
      --yellow: #fbbf24;
      --red: #f87171;
      --border: #2d3a4f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Segoe UI, system-ui, sans-serif;
      background: linear-gradient(180deg, #0b1017 0%, #121926 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 28px 20px 48px; }}
    .hero {{
      display: flex; justify-content: space-between; align-items: center; gap: 16px;
      margin-bottom: 24px; flex-wrap: wrap;
    }}
    h1 {{ margin: 0; font-size: 1.8rem; }}
    .subtitle {{ color: var(--muted); margin-top: 6px; }}
    .status-pill {{
      display: inline-flex; align-items: center; gap: 8px;
      background: var(--panel); border: 1px solid var(--border);
      padding: 10px 14px; border-radius: 999px; font-size: 0.92rem;
    }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--green); }}
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px; margin-bottom: 22px;
    }}
    .card {{
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 14px; padding: 18px;
    }}
    .card h3 {{ margin: 0 0 8px; color: var(--muted); font-size: 0.85rem; font-weight: 600; }}
    .card .num {{ font-size: 1.8rem; font-weight: 700; }}
    .panel {{
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 14px; padding: 18px; margin-bottom: 18px;
    }}
    .panel h2 {{ margin: 0 0 14px; font-size: 1.1rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .badge {{
      display: inline-block; padding: 4px 8px; border-radius: 999px;
      font-size: 0.75rem; font-weight: 700;
    }}
    .badge.alert {{ background: rgba(52, 211, 153, 0.15); color: var(--green); }}
    .badge.skip {{ background: rgba(147, 164, 187, 0.15); color: var(--muted); }}
    .badge.ok {{ background: rgba(52, 211, 153, 0.15); color: var(--green); }}
    .badge.bad {{ background: rgba(248, 113, 113, 0.15); color: var(--red); }}
    .empty {{ color: var(--muted); text-align: center; }}
    .meta {{ color: var(--muted); line-height: 1.7; }}
    code {{
      background: var(--panel-2); padding: 2px 6px; border-radius: 6px;
      word-break: break-all;
    }}
    .btn {{
      background: var(--accent); color: white; border: none;
      padding: 12px 18px; border-radius: 10px; font-weight: 700; cursor: pointer;
    }}
    .btn:hover {{ filter: brightness(1.08); }}
    .hint {{ color: var(--muted); margin-top: 10px; min-height: 20px; }}
    .actions {{ margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>Mail Checker Agent</h1>
        <p class="subtitle">Monitors recruiter interest and skips generic job auto-replies.</p>
      </div>
      <div class="status-pill"><span class="dot"></span> Agent online</div>
    </div>

    <div class="grid">
      <div class="card"><h3>Total Checks</h3><div class="num">{esc(stats.get('total_runs', 0))}</div></div>
      <div class="card"><h3>Alerts Sent</h3><div class="num">{esc(stats.get('total_alerts', 0))}</div></div>
      <div class="card"><h3>Emails Processed</h3><div class="num">{esc(stats.get('total_emails', 0))}</div></div>
      <div class="card"><h3>Auto-Skipped</h3><div class="num">{esc(stats.get('total_skipped', 0))}</div></div>
    </div>

    <div class="panel">
      <h2>Agent Config</h2>
      <div class="meta">
        <div><strong>Monitored inbox:</strong> {esc(settings_info.get('email_address'))}</div>
        <div><strong>Alert email:</strong> {esc(settings_info.get('alert_email'))}</div>
        <div><strong>Your name:</strong> {esc(settings_info.get('your_name') or 'Not set')}</div>
        <div><strong>Groq model:</strong> {esc(settings_info.get('groq_model'))}</div>
        <div><strong>Last check:</strong> {esc(last_run_text)} ({esc(last_run_status)})</div>
      </div>
      <div class="actions">{run_button}</div>
    </div>

    <div class="panel">
      <h2>Google Sheets / Script Trigger URL</h2>
      <p class="meta">Use this URL in your Google Apps Script time trigger:</p>
      <p><code>{esc(trigger_url)}</code></p>
    </div>

    <div class="panel">
      <h2>Recent Check Runs</h2>
      <table>
        <thead>
          <tr><th>Started</th><th>Found</th><th>Processed</th><th>Alerts</th><th>Status</th></tr>
        </thead>
        <tbody>{run_rows}</tbody>
      </table>
    </div>

    <div class="panel">
      <h2>Recent Emails</h2>
      <table>
        <thead>
          <tr><th>Result</th><th>Subject</th><th>Sender</th><th>Category</th><th>Reason</th><th>Time</th></tr>
        </thead>
        <tbody>{email_rows}</tbody>
      </table>
    </div>
  </div>

  <script>
    async function runCheck() {{
      const btn = document.getElementById('runBtn');
      const status = document.getElementById('runStatus');
      btn.disabled = true;
      status.textContent = 'Running inbox check...';
      try {{
        const res = await fetch('/check');
        const text = await res.text();
        status.textContent = res.ok ? text : ('Error: ' + text);
        if (res.ok) setTimeout(() => location.reload(), 1200);
      }} catch (err) {{
        status.textContent = 'Request failed: ' + err;
      }} finally {{
        btn.disabled = false;
      }}
    }}

    setInterval(() => location.reload(), 60000);
  </script>
</body>
</html>"""
