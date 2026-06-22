# Mail Checker

Monitors your inbox and alerts you when a recruiter shows real interest, sends an interview or test round, selects or rejects you, or shares another important job update.
It only checks unread emails from today, so old unread emails are ignored.
It skips OTP, password reset, login, and security emails from the subject line before reading the body or sending anything to AI.

Uses Groq (`llama-3.3-70b-versatile`) for fast AI classification.

## Live dashboard

After deploy, open your Render URL:

```text
https://mail-checker-1ips.onrender.com
```

The dashboard shows:
- Total checks, alerts sent, emails processed
- Recent check runs and classified emails
- Your Google Sheets trigger URL
- Run Check Now button
- iPhone home-screen push notifications

Example:

```text
https://mail-checker-1ips.onrender.com
```

## Deploy on Render

1. Go to [render.com](https://render.com), then choose **New** and **Blueprint**.
2. Connect repo `bagheldiwakar/Mail-checker`.
3. Add secret environment variables:

| Variable | Value |
|----------|-------|
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail app password |
| `GROQ_API_KEY` | Your Groq API key |
| `YOUR_NAME` | Your name |
| `ALERT_EMAIL` | Email to receive alerts |

4. Deploy. The free plan is set in `render.yaml`.

## Trigger with Google Apps Script

In Google Apps Script:

```javascript
function checkRecruiterMail() {
  var url = "https://mail-checker-1ips.onrender.com/check";
  var response = UrlFetchApp.fetch(url);
  Logger.log(response.getContentText());
}
```

Set a time-driven trigger, like every 5 to 15 minutes, on `checkRecruiterMail`.

## iPhone notifications

On iPhone, a normal browser tab will not ask for notification permission. Open the Render URL in Safari, share it, and choose **Add to Home Screen**. Open Mail Checker from the new Home Screen icon, then tap **Enable Notifications**.

Notification behavior:
- Manual **Run Check Now** sends a test-style phone notification after every run when notifications are enabled.
- Google Apps Script `/check` sends a phone notification only when important mail is found.
- Email alerts still work through `ALERT_EMAIL`.

## How to verify it is working

1. Open the dashboard. You should see "Agent online" and config details.
2. Health check: visit `/health`. It should return `OK`.
3. Manual test: open:

```text
https://mail-checker-1ips.onrender.com/check
```

The response should look like: `Processed 0 email(s), sent 0 alert(s), skipped 0.`

4. Dashboard updates: after a check, "Recent Check Runs" shows a new row.
5. Real alert test: send yourself a test email like:

> "Hi Diwakar, I reviewed your profile and would like to schedule an interview."

Leave it unread, run a check, and you should get an alert email at `ALERT_EMAIL`.

Check the Render **Logs** tab if anything fails.

## Run locally on Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
copy .env.example .env
python src/server.py
```

Open `http://localhost:10000`.

Local CLI mode, without the dashboard:

```powershell
python src/main.py --once
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | Required. Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model for classification |
| `EMAIL_ADDRESS` | - | Required. Inbox to monitor |
| `EMAIL_PASSWORD` | - | Required. App password |
| `ALERT_EMAIL` | same as `EMAIL_ADDRESS` | Where alert emails are sent |
| `MAX_EMAILS_PER_CHECK` | `5` | How many unread emails to check per run |
| `GROQ_REQUEST_DELAY_SECONDS` | `2` | Pause between AI calls to avoid rate limits |
| `NOTIFIER_MODE` | `auto` | `auto`, `desktop`, or `email` |
| `YOUR_NAME` | - | Helps AI detect personalized outreach |

## How it works

```text
Google Apps Script timer -> /check -> IMAP inbox -> Groq classify -> Email alert + Dashboard
```

After a Render redeploy or restart, open the iPhone Home Screen app and tap **Enable Notifications** again if phone alerts stop. The phone notification token is stored on the Render server, so redeploys can remove it on the free plan.
