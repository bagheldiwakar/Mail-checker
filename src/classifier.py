import json
import re
from dataclasses import dataclass

from groq import Groq

from email_fetcher import IncomingMail


@dataclass
class ClassificationResult:
    is_interesting: bool
    category: str
    reason: str
    urgency: str


SYSTEM_PROMPT = """You classify incoming emails for a job seeker.

Mark as INTERESTING (alert the user) when the email is important for the job search, such as:
- A recruiter personally reaching out about a role or your profile
- Invitation to interview, phone screen, HR round, technical round, test round, assignment, or assessment
- Selected, shortlisted, moved to next round, or offer-related emails
- Follow-up asking for availability, resume, or more details
- A hiring manager expressing interest after reviewing the profile
- Direct outreach from a company (not a mass job board blast)
- Rejection emails or application result/status emails that say the user was not selected

Mark as NOT INTERESTING (ignore) when the email is:
- Generic "thank you for applying" or "we received your application"
- Automated ATS status updates that only say the application is received, under review, or still being processed
- Mass job alerts, newsletters, or LinkedIn "jobs you may like"
- Marketing, spam, or unrelated mail

Be strict: only flag emails that deserve the user's attention because they contain an outcome, recruiter contact, interview, test, assessment, next step, offer, or rejection."""


def _build_user_prompt(mail: IncomingMail, your_name: str) -> str:
    name_hint = f"The job seeker's name is: {your_name}\n" if your_name else ""
    return f"""{name_hint}Classify this email:

From: {mail.sender} <{mail.sender_email}>
Subject: {mail.subject}

Body:
{mail.body[:6000]}

Respond with JSON only:
{{
  "is_interesting": true or false,
  "category": "recruiter_outreach | interview_invite | test_round | selected | follow_up | rejection | auto_reply | newsletter | other",
  "reason": "one short sentence",
  "urgency": "high | medium | low"
}}"""


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


class JobMailClassifier:
    def __init__(self, api_key: str, model: str, your_name: str = ""):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.your_name = your_name

    def classify(self, mail: IncomingMail) -> ClassificationResult:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(mail, self.your_name)},
            ],
        )

        content = response.choices[0].message.content or "{}"
        data = _parse_json(content)

        return ClassificationResult(
            is_interesting=bool(data.get("is_interesting", False)),
            category=str(data.get("category", "other")),
            reason=str(data.get("reason", "")),
            urgency=str(data.get("urgency", "low")),
        )
