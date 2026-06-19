# Mail Checker

Monitors your inbox and alerts you when a recruiter shows **real interest** — not generic "thanks for applying" auto-replies.

Uses **Groq** (`llama-3.3-70b-versatile`) for fast, free AI classification.

## Live dashboard

After deploy, open your Render URL:

```
https://mail-checker-1ips.onrender.com
```

The dashboard shows:
- Total checks, alerts sent, emails processed
- Recent check runs and classified emails
- Your Google Sheets trigger URL
- **Run Check Now** button (add `?secret=YOUR_CRON_SECRET` to the URL)

Example:
```
https://mail-checker-1ips.onrender.com?secret=YOUR_CRON_SECRET
```

---

## Deploy on Render (free, no credit card)

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect repo `bagheldiwakar/Mail-checker`
3. Add secret environment variables:

| Variable | Value |
|----------|-------|
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail [App Password](https://myaccount.google.com/apppasswords) |
| `GROQ_API_KEY` | Your Groq API key |
| `YOUR_NAME` | Your name |
| `ALERT_EMAIL` | Email to receive alerts |

4. Deploy — `plan: free` is set in `render.yaml`

Copy `CRON_SECRET` from Render → Environment tab after deploy.

---

## Trigger with Google Sheets (time trigger)

In Google Apps Script:

```javascript
function checkRecruiterMail() {
  var secret = "YOUR_CRON_SECRET";
  var url = "https://mail-checker-1ips.onrender.com/check?secret=" + secret;
  var response = UrlFetchApp.fetch(url);
  Logger.log(response.getContentText());
}
```

Set a **time-driven trigger** (every 5–15 minutes) on `checkRecruiterMail`.

---

## How to verify it is working

1. **Open the dashboard** — you should see "Agent online" and config details (not "Not found").
2. **Health check** — visit `/health` → should return `OK`.
3. **Manual test** — open:
   ```
   https://mail-checker-1ips.onrender.com/check?secret=YOUR_CRON_SECRET
   ```
   Response should be like: `Processed 0 email(s), sent 0 alert(s), skipped 0.`
4. **Dashboard updates** — after a check, "Recent Check Runs" shows a new row.
5. **Real alert test** — send yourself a test email like:
   > "Hi Diwakar, I reviewed your profile and would like to schedule an interview."
   
   Leave it unread, run a check, and you should get an alert email at `ALERT_EMAIL`.

Check Render **Logs** tab if anything fails.

---

## Run locally on Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
copy .env.example .env
python src/server.py
```

Open `http://localhost:10000`

Local CLI mode (no dashboard):

```powershell
python src/main.py --once
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Required. Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model for classification |
| `EMAIL_ADDRESS` | — | Required. Inbox to monitor |
| `EMAIL_PASSWORD` | — | Required. App password |
| `ALERT_EMAIL` | same as `EMAIL_ADDRESS` | Where alert emails are sent |
| `CRON_SECRET` | — | Token for `/check` endpoint |
| `NOTIFIER_MODE` | `auto` | `auto`, `desktop`, or `email` |
| `YOUR_NAME` | — | Helps AI detect personalized outreach |

---

## How it works

```
Google Sheets trigger → /check → IMAP inbox → Groq classify → Email alert + Dashboard
```
