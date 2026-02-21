# Majordomo

> *noun* — a person who manages a great household on behalf of their employer. In this case, the household is your inbox, the employer is you, and the employee never sleeps, never complains, and never accidentally replies-all.

Majordomo is a fully autonomous AI agent that monitors a dedicated inbox and replies to emails without human intervention. You set a persona, point it at a mailbox, and walk away. It handles everything else — including the emails you were never going to answer anyway.

## Architecture

```
IMAP poll → triage (LLM) → generate reply (LLM) → send via SMTP
```

Uses **LangGraph** for the agent loop and **Claude** as the LLM. No database. No UI. No drama.

## Setup

### 1. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure
Copy `config.py.template` and fill in your values, or set environment variables:

```bash
export EMAIL_ADDRESS="agent@yourdomain.com"
export EMAIL_PASSWORD="your-app-password"
export IMAP_HOST="imap.gmail.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="465"
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_BASE_URL="https://yourfavorite"
export LLM_MODEL="yourmodel"
export AGENT_NAME="Alex"
export AGENT_PERSONA="a helpful assistant for Acme Corp..."
export POLL_INTERVAL_SECONDS="60"
```

### 4. Gmail setup (if using Gmail)
- Create a dedicated Gmail account for the agent
- Enable 2FA and generate an **App Password**
- Use the App Password as `EMAIL_PASSWORD`

### 5. Run
```bash
python agent.py
```

Majordomo will now handle your correspondence. You may go touch grass.

## How it works

1. **Poll** — checks for UNSEEN emails every N seconds via IMAP
2. **Triage** — decides if the email warrants a reply (filters spam, auto-replies, newsletters, and the guy who keeps emailing about his invoice)
3. **Generate** — writes a reply in your persona and tone
4. **Send** — sends via SMTP and marks the original as Seen, as if it were never a problem

## Compared to the fancy alternatives

**[Inbox Zero](https://github.com/elie222/inbox-zero)** is a full web product that keeps you in the loop — it drafts, you approve. Very sensible. Majordomo does not ask for your approval. Majordomo has already replied.

**[Zero (Mail-0)](https://github.com/Mail-0/Zero)** is a beautiful open-source email client — a better Gmail, basically. You still sit there and read things. Majordomo thinks that sounds exhausting.
