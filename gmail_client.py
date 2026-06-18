import base64
import logging
import os
from typing import Any, Dict, List, Optional

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


from config import CREDENTIALS_FILE, SCOPES, TOKEN_FILE

log = logging.getLogger(__name__)


def get_gmail_service():
    """Authenticate and return a Gmail API service object."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        log.info("Loaded saved Gmail token.")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                log.error(
                    f"'{CREDENTIALS_FILE.name}' not found. Download it from Google Cloud Console."
                )
                raise FileNotFoundError(CREDENTIALS_FILE)
            log.info("Opening browser for Gmail login...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        log.info("Gmail token saved.")

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload: Dict[str, Any]) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text
    elif payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return "[Body could not be extracted]"


def _parse_email(message: Dict[str, Any]) -> Dict[str, Any]:
    headers = message.get("payload", {}).get("headers", [])
    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
    recipient = next((h["value"] for h in headers if h["name"] == "To"), "")
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")
    body = _extract_body(message.get("payload", {}))
    sender_name = sender.split("<")[0].strip().strip('"') if "<" in sender else sender.split("@")[0]

    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "sender": sender,
        "sender_name": sender_name,
        "recipient": recipient,
        "subject": subject,
        "date": date_str,
        "body": body[:3000],
    }


def get_unread_emails(service, max_results: int = 5) -> List[Dict[str, Any]]:
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=["INBOX", "UNREAD"],
            maxResults=max_results,
        ).execute()
    except HttpError as e:
        log.error(f"Gmail API error: {e}")
        return []

    emails = []
    for msg in result.get("messages", []):
        try:
            full = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full",
            ).execute()
            emails.append(_parse_email(full))
        except HttpError as e:
            log.warning(f"Could not fetch {msg['id']}: {e}")

    return emails


def create_gmail_draft(service, email: Dict[str, Any], reply_text: str) -> Optional[str]:
    """Save a reply to an existing email thread as a draft."""
    msg = MIMEMultipart()
    msg["To"] = email["sender"]
    msg["Subject"] = f"Re: {email['subject']}"
    msg.attach(MIMEText(reply_text, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw, "threadId": email["thread_id"]}},
        ).execute()
        return draft.get("id")
    except HttpError as e:
        log.error(f"Failed to save draft: {e}")
        return None


def create_new_gmail_draft(service, recipient: str, subject: str, body: str) -> Optional[str]:
    """Create a brand-new draft email."""
    msg = MIMEMultipart()
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
        return draft.get("id")
    except HttpError as e:
        log.error(f"Failed to save new draft: {e}")
        return None


def send_gmail_message(
    service,
    recipient: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
) -> Optional[str]:
    """Send a message immediately."""
    msg = MIMEMultipart()
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        message_body = {"raw": raw}
        if thread_id:
            message_body["threadId"] = thread_id
        sent = service.users().messages().send(
            userId="me",
            body=message_body,
        ).execute()
        return sent.get("id")
    except HttpError as e:
        log.error(f"Failed to send email: {e}")
        return None


def is_watched_sender(email: Dict[str, Any], watched_senders: Optional[List[str]] = None) -> bool:
    sender_lower = email["sender"].lower()
    senders = watched_senders or []
    return any(w.lower() in sender_lower for w in senders)
