# Mail Checker

Monitors your inbox and alerts you when a recruiter shows **real interest** — not generic "thanks for applying" auto-replies.

Uses **Groq** (`llama-3.3-70b-versatile`) for fast, free AI classification.

## What it catches

- Recruiter personally reaching out about your profile
- Interview / phone screen invitations
- Follow-ups asking for availability or more info

## What it ignores

- "Thank you for applying" auto-replies
- ATS status updates and rejections
- Job newsletters and mass alerts

---

## Deploy on Render (100% free, no credit card)

Render **cron jobs cost money** and require a card. This project uses a **free web service** instead.

### Step 1 — Deploy on Render

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect repo `bagheldiwakar/Mail-checker`
3. Add these secret environment variables:

| Variable | Value |
|----------|-------|
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail [App Password](https://myaccount.google.com/apppasswords) |
| `GROQ_API_KEY` | Your Groq API key from [console.groq.com](https://console.groq.com) |
| `YOUR_NAME` | Your name |
| `ALERT_EMAIL` | Email to receive alerts |

4. Click **Apply** — `plan: free` is set in `render.yaml` (no card needed)
5. After deploy, open the service → **Environment** → copy the auto-generated `CRON_SECRET`

### Step 2 — Schedule checks (free, no card)

Use [cron-job.org](https://cron-job.org) (free):

1. Create a free account
2. **Create cronjob** → URL:
   ```
   https://YOUR-RENDER-URL.onrender.com/check?secret=YOUR_CRON_SECRET
   ```
3. Schedule: every **5 minutes**
4. Save

Each ping wakes the free web service and runs one inbox check. You get an alert email when recruiter interest is detected.

> **Note:** Free Render services spin down after ~15 min idle. The cron-job.org ping wakes them up (~30 sec cold start). This is normal on the free tier.

---

## Run locally on Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
copy .env.example .env
# Edit .env with your credentials
python src/main.py
```

Local mode uses **Windows toast notifications + sound**. Set `NOTIFIER_MODE=email` in `.env` to test email alerts instead.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Required. Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Best free Groq model for classification |
| `EMAIL_ADDRESS` | — | Required. Inbox to monitor |
| `EMAIL_PASSWORD` | — | Required. App password |
| `ALERT_EMAIL` | same as `EMAIL_ADDRESS` | Where alert emails are sent |
| `CRON_SECRET` | — | Token for `/check` endpoint (Render generates this) |
| `NOTIFIER_MODE` | `auto` | `auto`, `desktop`, or `email` |
| `POLL_INTERVAL` | `120` | Seconds between checks (local mode only) |
| `YOUR_NAME` | — | Helps AI detect personalized outreach |

---

## How it works

```
cron-job.org (every 5 min) → Render /check → IMAP inbox → Groq classify → Email alert
```

Processed emails are marked as read on IMAP to avoid duplicate alerts on Render's temporary filesystem.
