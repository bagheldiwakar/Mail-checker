import html
from urllib.parse import quote


def _gmail_message_url(gmail_thread_id, message_id) -> str:
    gmail_thread_id = str(gmail_thread_id or "").strip()
    if gmail_thread_id:
        return "https://mail.google.com/mail/u/0/#all/" + quote(
            gmail_thread_id,
            safe="",
        )

    message_id = str(message_id or "").strip()
    if not message_id or message_id.startswith("uid-"):
        return ""
    return "https://mail.google.com/mail/u/0/#search/" + quote(
        f"rfc822msgid:{message_id}",
        safe="",
    )


def _gmail_app_message_url(gmail_thread_id) -> str:
    gmail_thread_id = str(gmail_thread_id or "").strip()
    if not gmail_thread_id:
        return ""
    thread_id = quote(gmail_thread_id, safe="")
    return f"googlegmail:///cv={thread_id}/accountId=1&create-new-tab"


def render_dashboard(
    settings_info: dict,
    stats: dict,
    active_alerts: list,
    recent_emails: list,
    recent_runs: list,
) -> str:
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
        email_rows = '<tr><td colspan="6" class="empty">No emails processed yet.</td></tr>'

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

    alert_cards = ""
    if active_alerts:
        for alert in active_alerts:
            company = alert.get("company_name") or alert.get("sender") or "Unknown company"
            profile = alert.get("job_profile") or alert.get("subject") or "Job update"
            gmail_url = _gmail_message_url(
                alert.get("gmail_thread_id"),
                alert.get("message_id"),
            )
            gmail_app_url = _gmail_app_message_url(alert.get("gmail_thread_id"))
            card_class = "alert-card clickable" if gmail_url else "alert-card"
            open_attrs = (
                f'role="link" tabindex="0" data-gmail-url="{esc(gmail_url)}" '
                f'data-gmail-app-url="{esc(gmail_app_url)}" '
                f'aria-label="Open {esc(profile)} in Gmail" '
                'onclick="openMailFromCard(this)" '
                'onkeydown="openMailFromCardKey(event, this)"'
                if gmail_url
                else ""
            )
            alert_cards += f"""
            <article class="{card_class}" {open_attrs}>
              <div>
                <div class="alert-topline">{esc(alert.get('category') or 'job_alert')}</div>
                <h3>{esc(profile)}</h3>
                <div class="alert-meta">
                  <span><strong>Company:</strong> {esc(company)}</span>
                  <span><strong>Sender:</strong> {esc(alert.get('sender'))}</span>
                  <span><strong>Time:</strong> {esc(alert.get('processed_at'))}</span>
                </div>
                <p>{esc(alert.get('reason'))}</p>
              </div>
              <button class="btn secondary compact" data-message-id="{esc(alert.get('message_id'))}" onclick="dismissAlert(event, this)">Remove</button>
            </article>"""
    else:
        alert_cards = '<p class="empty">No active important mail to track.</p>'

    last_run = stats.get("last_run") or {}
    last_run_text = last_run.get("finished_at") or last_run.get("started_at") or "Never"
    last_run_status = last_run.get("status") or "waiting"
    trigger_url = settings_info.get("trigger_url", "")
    push_subscriptions = int(settings_info.get("push_subscriptions", 0) or 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#f5f5f7">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Mail Checker">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <link rel="manifest" href="/manifest.json">
  <link rel="apple-touch-icon" href="/app-icon.svg">
  <title>Mail Checker</title>
  <style>
    :root {{
      --bg: #f5f5f7;
      --surface: rgba(255, 255, 255, 0.78);
      --surface-strong: #ffffff;
      --text: #1d1d1f;
      --muted: #6e6e73;
      --line: rgba(0, 0, 0, 0.08);
      --blue: #0071e3;
      --green: #248a3d;
      --red: #d70015;
      --shadow: 0 18px 44px rgba(0, 0, 0, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--bg); }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(0, 113, 227, 0.14), transparent 34rem),
        linear-gradient(180deg, #fbfbfd 0%, var(--bg) 45%, #efeff4 100%);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", system-ui, sans-serif;
    }}
    .wrap {{
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: max(22px, env(safe-area-inset-top)) 18px 44px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin-bottom: 26px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }}
    .appicon {{
      width: 46px;
      height: 46px;
      border-radius: 14px;
      background: #111;
      display: grid;
      place-items: center;
      box-shadow: var(--shadow);
      flex: 0 0 auto;
    }}
    .appicon::before {{
      content: "";
      width: 25px;
      height: 16px;
      border-radius: 5px;
      background: #fff;
      box-shadow: 10px -9px 0 -4px #30d158;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(1.55rem, 4vw, 2.45rem);
      line-height: 1.05;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 0.96rem;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.62);
      color: var(--muted);
      white-space: nowrap;
    }}
    .dot {{
      width: 9px;
      height: 9px;
      border-radius: 99px;
      background: var(--green);
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel, .card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(22px);
    }}
    .panel {{ padding: 18px; margin-bottom: 18px; }}
    .primary {{
      padding: clamp(20px, 4vw, 34px);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 248px;
    }}
    .primary h2 {{
      margin: 0;
      max-width: 760px;
      font-size: clamp(2rem, 7vw, 4.8rem);
      line-height: 0.98;
      letter-spacing: 0;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 24px;
      align-items: center;
    }}
    .btn {{
      min-height: 44px;
      border: 0;
      border-radius: 999px;
      padding: 0 18px;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      font-size: 0.95rem;
    }}
    .btn.secondary {{
      background: #e8e8ed;
      color: var(--text);
    }}
    .btn.compact {{
      min-height: 36px;
      padding: 0 14px;
      font-size: 0.86rem;
      flex: 0 0 auto;
    }}
    .btn:disabled {{
      cursor: not-allowed;
      opacity: 0.58;
    }}
    .hint {{
      width: 100%;
      min-height: 22px;
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .card {{ padding: 18px; min-height: 118px; }}
    .card h3 {{
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .num {{
      font-size: clamp(1.8rem, 6vw, 2.8rem);
      font-weight: 800;
      line-height: 1;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 1.08rem;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      line-height: 1.8;
      overflow-wrap: anywhere;
    }}
    code {{
      display: inline-block;
      max-width: 100%;
      background: #f0f0f3;
      border: 1px solid var(--line);
      padding: 8px 10px;
      border-radius: 8px;
      color: #333;
      overflow-wrap: anywhere;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
      min-width: 720px;
    }}
    th, td {{
      padding: 11px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 700; }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.76rem;
      font-weight: 800;
    }}
    .badge.alert, .badge.ok {{ background: rgba(36, 138, 61, 0.12); color: var(--green); }}
    .badge.skip {{ background: rgba(110, 110, 115, 0.14); color: var(--muted); }}
    .badge.bad {{ background: rgba(215, 0, 21, 0.12); color: var(--red); }}
    .empty {{ color: var(--muted); text-align: center; }}
    .alerts-list {{
      display: grid;
      gap: 12px;
    }}
    .alert-card {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.72);
    }}
    .alert-card.clickable {{
      cursor: pointer;
      transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
    }}
    .alert-card.clickable:hover,
    .alert-card.clickable:focus-visible {{
      background: #ffffff;
      border-color: rgba(0, 113, 227, 0.34);
      transform: translateY(-1px);
      outline: none;
    }}
    .alert-card h3 {{
      margin: 4px 0 8px;
      font-size: 1.12rem;
      line-height: 1.25;
    }}
    .alert-card p {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .alert-topline {{
      color: var(--blue);
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .alert-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 0.9rem;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 760px) {{
      .topbar, .hero {{ display: block; }}
      .status-pill {{ margin-top: 16px; }}
      .primary {{ min-height: 276px; margin-bottom: 14px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .alert-card {{ display: block; }}
      .alert-card .btn {{ margin-top: 14px; }}
      .card {{ min-height: 104px; padding: 14px; }}
      .wrap {{ padding-left: 14px; padding-right: 14px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="topbar">
      <div class="brand">
        <div class="appicon" aria-hidden="true"></div>
        <div>
          <h1>Mail Checker</h1>
          <p class="subtitle">Today-only job alerts, filtered by AI.</p>
        </div>
      </div>
      <div class="status-pill"><span class="dot"></span> Agent online</div>
    </header>

    <section class="hero">
      <div class="panel primary">
        <div>
          <h2>Recruiter signals, without the inbox noise.</h2>
        </div>
        <div class="actions">
          <button class="btn" id="runBtn" onclick="runCheck()">Run Check Now</button>
          <button class="btn secondary" id="notifyBtn" onclick="enableNotifications()">Enable Notifications</button>
          <p id="runStatus" class="hint"></p>
        </div>
      </div>
      <div class="grid">
        <div class="card"><h3>Total Checks</h3><div class="num">{esc(stats.get('total_runs', 0))}</div></div>
        <div class="card"><h3>Alerts Sent</h3><div class="num">{esc(stats.get('total_alerts', 0))}</div></div>
        <div class="card"><h3>Processed</h3><div class="num">{esc(stats.get('total_emails', 0))}</div></div>
        <div class="card"><h3>Skipped</h3><div class="num">{esc(stats.get('total_skipped', 0))}</div></div>
      </div>
    </section>

    <section class="panel">
      <h2>Important Mail To Track</h2>
      <div class="alerts-list">
        {alert_cards}
      </div>
    </section>

    <section class="panel">
      <h2>Agent Config</h2>
      <div class="meta">
        <div><strong>Monitored inbox:</strong> {esc(settings_info.get('email_address'))}</div>
        <div><strong>Alert email:</strong> {esc(settings_info.get('alert_email'))}</div>
        <div><strong>Your name:</strong> {esc(settings_info.get('your_name') or 'Not set')}</div>
        <div><strong>Groq model:</strong> {esc(settings_info.get('groq_model'))}</div>
        <div><strong>Last check:</strong> {esc(last_run_text)} ({esc(last_run_status)})</div>
        <div><strong>Phone notification tokens:</strong> {esc(push_subscriptions)}</div>
      </div>
    </section>

    <section class="panel">
      <h2>Google Apps Script Trigger URL</h2>
      <p><code>{esc(trigger_url)}</code></p>
    </section>

    <section class="panel">
      <h2>Recent Check Runs</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Started</th><th>Found</th><th>Processed</th><th>Alerts</th><th>Status</th></tr>
          </thead>
          <tbody>{run_rows}</tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>Recent Emails</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Result</th><th>Subject</th><th>Sender</th><th>Category</th><th>Reason</th><th>Time</th></tr>
          </thead>
          <tbody>{email_rows}</tbody>
        </table>
      </div>
    </section>
  </div>

    <script>
    const statusEl = document.getElementById('runStatus');
    const notifyBtn = document.getElementById('notifyBtn');
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true;

    function setStatus(message) {{
      statusEl.textContent = message || '';
    }}

    function urlBase64ToUint8Array(base64String) {{
      const padding = '='.repeat((4 - base64String.length % 4) % 4);
      const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
      const rawData = window.atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      for (let i = 0; i < rawData.length; ++i) {{
        outputArray[i] = rawData.charCodeAt(i);
      }}
      return outputArray;
    }}

    function notificationHelpMessage() {{
      if (isIos && !isStandalone) {{
        return 'On iPhone, open this site in Safari, tap Share, Add to Home Screen, then open from the new icon.';
      }}
      if (!('Notification' in window)) {{
        return 'This browser cannot show website notifications.';
      }}
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {{
        return 'Push notifications are not available here. On iPhone, use the Home Screen app.';
      }}
      return '';
    }}

    async function getServiceWorkerRegistration() {{
      const existing = await navigator.serviceWorker.getRegistration('/');
      if (existing) return existing;
      return navigator.serviceWorker.register('/service-worker.js');
    }}

    async function showLocalNotification(title, body) {{
      if (!('Notification' in window) || Notification.permission !== 'granted') {{
        return false;
      }}
      if (!('serviceWorker' in navigator)) {{
        return false;
      }}

      const registration = await getServiceWorkerRegistration();
      await navigator.serviceWorker.ready;
      await registration.showNotification(title, {{
        body,
        icon: '/app-icon.svg',
        badge: '/app-icon.svg',
        data: {{ url: '/' }}
      }});
      return true;
    }}

    async function enableNotifications() {{
      const help = notificationHelpMessage();
      if (help) {{
        setStatus(help);
        return;
      }}

      notifyBtn.disabled = true;
      setStatus('Preparing notifications...');
      try {{
        const registration = await getServiceWorkerRegistration();
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {{
          setStatus('Notification permission was not allowed.');
          return;
        }}

        const keyRes = await fetch('/api/push/public-key');
        const keyData = await keyRes.json();
        const subscription = await registration.pushManager.subscribe({{
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(keyData.publicKey)
        }});

        const saveRes = await fetch('/api/push/subscribe', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(subscription)
        }});
        if (!saveRes.ok) throw new Error(await saveRes.text());
        await showLocalNotification('Mail Checker notifications enabled', 'This is your test notification.');
        setStatus('Notifications enabled. A test notification was sent.');
      }} catch (err) {{
        setStatus('Notification setup failed: ' + err.message);
      }} finally {{
        notifyBtn.disabled = false;
      }}
    }}

    async function runCheck() {{
      const btn = document.getElementById('runBtn');
      btn.disabled = true;
      setStatus('Running inbox check...');
      try {{
        const res = await fetch('/check?source=manual');
        const text = await res.text();
        setStatus(res.ok ? text : ('Error: ' + text));
        if (res.ok) {{
          const shown = await showLocalNotification('Manual mail check finished', text || 'Notifications are working.');
          if (!shown) {{
            const help = notificationHelpMessage();
            if (help) {{
              setStatus(text + ' ' + help);
            }} else {{
              setStatus(text + ' Enable notifications to receive phone alerts.');
            }}
          }}
          setTimeout(() => location.reload(), 1800);
        }}
      }} catch (err) {{
        setStatus('Request failed: ' + err.message);
      }} finally {{
        btn.disabled = false;
      }}
    }}

    function openMailFromCard(card) {{
      const gmailUrl = card.getAttribute('data-gmail-url');
      if (!gmailUrl) return;

      const gmailAppUrl = card.getAttribute('data-gmail-app-url');
      if (isIos && gmailAppUrl) {{
        let fallbackTimer = window.setTimeout(() => {{
          window.location.href = gmailUrl;
        }}, 3000);

        const cancelFallback = () => {{
          window.clearTimeout(fallbackTimer);
          fallbackTimer = null;
        }};

        window.addEventListener('pagehide', cancelFallback, {{ once: true }});
        document.addEventListener('visibilitychange', () => {{
          if (document.hidden) cancelFallback();
        }}, {{ once: true }});

        window.location.href = gmailAppUrl;
        return;
      }}

      const opened = window.open(gmailUrl, '_blank', 'noopener');
      if (!opened) {{
        window.location.href = gmailUrl;
      }}
    }}

    function openMailFromCardKey(event, card) {{
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      openMailFromCard(card);
    }}

    async function dismissAlert(event, button) {{
      event.stopPropagation();
      const messageId = button.getAttribute('data-message-id');
      if (!messageId) return;
      button.disabled = true;
      try {{
        const res = await fetch('/api/alerts/dismiss', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ message_id: messageId }})
        }});
        if (!res.ok) throw new Error(await res.text());
        setStatus('Removed from dashboard tracking.');
        setTimeout(() => location.reload(), 500);
      }} catch (err) {{
        button.disabled = false;
        setStatus('Remove failed: ' + err.message);
      }}
    }}

    if ('Notification' in window && Notification.permission === 'granted') {{
      setStatus('Notifications enabled.');
    }} else {{
      const help = notificationHelpMessage();
      if (help) setStatus(help);
    }}

    setInterval(() => location.reload(), 60000);
  </script>
</body>
</html>"""
