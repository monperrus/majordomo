# Autonomous Email Agent

A fully autonomous AI agent that monitors a dedicated inbox and replies to emails without human intervention.

## Architecture

```
IMAP poll → triage (LLM) → generate reply (LLM) → send via SMTP
```

Uses **LangGraph** for the agent loop and **Claude** as the LLM.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Copy `config.py.template` and fill in your values, or set environment variables:

```bash
export EMAIL_ADDRESS="agent@yourdomain.com"
export EMAIL_PASSWORD="your-app-password"
export IMAP_HOST="imap.gmail.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="465"
export ANTHROPIC_API_KEY="sk-ant-..."
export AGENT_NAME="Alex"
export AGENT_PERSONA="a helpful assistant for Acme Corp..."
export POLL_INTERVAL_SECONDS="60"
```

### 3. Gmail setup (if using Gmail)
- Create a dedicated Gmail account for the agent
- Enable 2FA and generate an **App Password**
- Use the App Password as `EMAIL_PASSWORD`

### 4. Run
```bash
python agent.py
```

## How it works

1. **Poll** — checks for UNSEEN emails every N seconds via IMAP
2. **Triage** — LLM decides if the email deserves a reply (filters spam, auto-replies, newsletters)
3. **Generate** — LLM writes a reply using your persona and system prompt
4. **Send** — sends via SMTP and marks the original as Seen

## Comparison with Inbox Zero

[Inbox Zero](https://github.com/elie222/inbox-zero) is a full-featured web product aimed at keeping a human in the loop — it drafts replies, organises labels, tracks follow-ups, and blocks cold emails, but you still decide what gets sent. This agent takes the opposite stance: it is fully autonomous and sends replies without any human approval.

## Extending

- **Memory**: store past threads in SQLite and pass them as context
- **Tools**: give the agent tools (calendar booking, CRM lookup, ticket creation)
- **Webhooks**: replace polling with Gmail Push Notifications or SendGrid Inbound Parse for real-time processing
- **Human-in-the-loop**: add an approval step that posts to Slack before sending
- **Multiple personas**: run multiple instances with different configs for different inboxes
