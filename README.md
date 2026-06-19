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

## Deploy on Render (free)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect repo `bagheldiwakar/Mail-checker`.
3. Add these **secret** environment variables in the Render dashboard:

| Variable | Value |
|----------|-------|
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail [App Password](https://myaccount.google.com/apppasswords) |
| `GROQ_API_KEY` | Your Groq API key from [console.groq.com](https://console.groq.com) |
| `YOUR_NAME` | Your name (helps AI spot personalized outreach) |
| `ALERT_EMAIL` | Email to receive alerts (can be same as `EMAIL_ADDRESS`) |

4. Deploy. Render runs a **cron job every 5 minutes** that checks your inbox and emails you when something important arrives.

> **Note:** Render's filesystem is temporary, so processed emails are marked as read on IMAP to avoid duplicate alerts.

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
| `NOTIFIER_MODE` | `auto` | `auto`, `desktop`, or `email` |
| `POLL_INTERVAL` | `120` | Seconds between checks (local mode only) |
| `YOUR_NAME` | — | Helps AI detect personalized outreach |

---

## How it works

```
Inbox (IMAP) → Fetch unread → Groq AI classify → Alert OR skip → Mark processed
```

Processed email IDs are stored in `data/processed.db` locally. On Render, emails are also marked as read via IMAP.
