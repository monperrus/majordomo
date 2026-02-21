"""
Autonomous Email Agent
- Polls a dedicated IMAP inbox
- Uses LangGraph to reason and decide on a reply
- Sends replies via SMTP automatically
"""

import imaplib
import smtplib
import email
import ssl
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ── State ──────────────────────────────────────────────────────────────────────

class EmailState(TypedDict):
    uid: str
    sender: str
    subject: str
    body: str
    thread_history: str
    is_auto_reply: bool
    should_reply: bool
    reply_body: str
    error: str


# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    model="x-ai/grok-4-fast",
    api_key=Config.ANTHROPIC_AUTH_TOKEN,
    base_url=Config.ANTHROPIC_BASE_URL + "/v1" if Config.ANTHROPIC_BASE_URL else None,
)


# ── Graph Nodes ───────────────────────────────────────────────────────────────

def triage(state: EmailState) -> EmailState:
    """Decide whether this email warrants a reply based on auto-reply headers."""
    state["should_reply"] = not state["is_auto_reply"]
    log.info(f"Triage for '{state['subject']}': {'REPLY' if state['should_reply'] else 'SKIP (auto-reply)'}")
    return state


def generate_reply(state: EmailState) -> EmailState:
    """Generate a reply to the email."""
    if not state["should_reply"]:
        return state

    thread_section = ""
    if state["thread_history"]:
        thread_section = f"\nPrevious thread context:\n{state['thread_history']}\n"

    prompt = f"""
{thread_section}

You received this email:
FROM: {state['sender']}
SUBJECT: {state['subject']}
BODY:
{state['body']}

Write a helpful, professional reply. Be concise. Do not use filler phrases like 
"I hope this email finds you well." Sign off as: {Config.AGENT_NAME}

Write only the email body, no subject line."""

    result = llm.invoke([
        SystemMessage(content=Config.AGENT_PERSONA),
        HumanMessage(content=prompt)
    ])
    state["reply_body"] = result.content.strip()
    return state


def send_reply(state: EmailState) -> EmailState:
    """Send the generated reply via SMTP."""
    if not state["should_reply"] or not state["reply_body"]:
        return state

    try:
        msg = MIMEMultipart()
        msg["From"] = Config.EMAIL_ADDRESS
        msg["To"] = state["sender"]
        msg["Subject"] = f"Re: {state['subject']}"
        msg["Auto-Submitted"] = "auto-replied"
        msg.attach(MIMEText(state["reply_body"], "plain"))

        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            server.sendmail(Config.EMAIL_ADDRESS, state["sender"], msg.as_string())

        log.info(f"Replied to {state['sender']} re: '{state['subject']}'")
    except Exception as e:
        state["error"] = str(e)
        log.error(f"Failed to send reply: {e}")

    return state


def route_after_triage(state: EmailState) -> str:
    return "generate_reply" if state["should_reply"] else END


# ── Build Graph ────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(EmailState)
    graph.add_node("triage", triage)
    graph.add_node("generate_reply", generate_reply)
    graph.add_node("send_reply", send_reply)

    graph.set_entry_point("triage")
    graph.add_conditional_edges("triage", route_after_triage)
    graph.add_edge("generate_reply", "send_reply")
    graph.add_edge("send_reply", END)

    return graph.compile()


agent = build_graph()


# ── IMAP Helpers ───────────────────────────────────────────────────────────────

def decode_str(value):
    if not value:
        return ""
    parts = decode_header(value)
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in parts
    )


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""


AUTO_REPLY_HEADERS = {
    "auto-submitted",
    "x-auto-response-suppress",
    "x-autoreply",
    "x-autorespond",
}
AUTO_REPLY_PRECEDENCE = {"bulk", "list", "auto_reply", "junk"}


def is_auto_reply_email(msg) -> bool:
    """Return True if the message contains standard auto-reply headers."""
    auto_submitted = (msg.get("Auto-Submitted") or "").strip().lower()
    if auto_submitted and auto_submitted != "no":
        return True
    precedence = (msg.get("Precedence") or "").strip().lower()
    if precedence in AUTO_REPLY_PRECEDENCE:
        return True
    for h in ("X-Auto-Response-Suppress", "X-Autoreply", "X-Autorespond"):
        if msg.get(h) is not None:
            return True
    return False


def fetch_unseen_emails(imap):
    imap.select("INBOX")
    _, uids = imap.search(None, "UNSEEN")
    emails = []
    for uid in uids[0].split():
        _, data = imap.fetch(uid, "(RFC822)")
        raw = data[0][1]
        msg = email.message_from_bytes(raw)
        emails.append({
            "uid": uid.decode(),
            "sender": decode_str(msg["From"]),
            "subject": decode_str(msg["Subject"]),
            "body": get_body(msg),
            "thread_history": "",  # extend here with thread lookup if needed
            "is_auto_reply": is_auto_reply_email(msg),
        })
        # Mark as seen
        imap.store(uid, "+FLAGS", "\\Seen")
    return emails


# ── Main Loop ──────────────────────────────────────────────────────────────────

def run():
    log.info(f"Agent starting. Monitoring {Config.EMAIL_ADDRESS}")
    while True:
        try:
            ctx = ssl.create_default_context()
            with imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT, ssl_context=ctx) as imap:
                imap.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
                emails = fetch_unseen_emails(imap)

            log.info(f"Found {len(emails)} unseen email(s)")
            for e in emails:
                state: EmailState = {
                    "uid": e["uid"],
                    "sender": e["sender"],
                    "subject": e["subject"],
                    "body": e["body"],
                    "thread_history": e["thread_history"],
                    "is_auto_reply": e["is_auto_reply"],
                    "should_reply": False,
                    "reply_body": "",
                    "error": "",
                }
                agent.invoke(state)

        except Exception as e:
            raise e
            log.error(f"Poll error: {e}")

        time.sleep(Config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
