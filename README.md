<div align="center">

# 🏭 Personal Agentic Factory

**A local-first, multi-agent AI software factory that works for you 24/7.**
<br />
*Text it a task from your phone. Come home to a fully working app on your machine.*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Bot-Telegram-2CA5E0.svg?logo=telegram&logoColor=white)](https://telegram.org/)

</div>

---

## ⚡ What is PAF?

**Personal Agentic Factory (PAF)** is a highly autonomous, multi-agent system designed to build complete software projects from a single prompt. Unlike cloud-based agents, PAF runs **locally** on your machine, leveraging its state-recovery loop to survive crashes, internet drops, and API limits.

Drop an idea in a Telegram message, and it orchestrates three distinct AI agents:
1. 🧠 **The Architect** — Breaks your idea down into a technical specification and file plan.
2. 💻 **The Coder** — Writes complete, production-ready code (no annoying placeholders).
3. 🕵️ **The Auditor** — Runs the built code in a Docker sandbox, catches errors, and kicks failed code back to the Coder.

When the job is done, the **Liaison** packages the finished software and texts it directly to your phone as a `.zip` archive.

---

## ✨ Key Features

- **📱 Remote Triggering:** Start jobs on your PC from anywhere in the world via Telegram.
- **🔄 Auto-Retry & State Recovery:** Every step is safely checkpointed. If the process is interrupted, it resumes exactly where it left off. No lost progress, no wasted API credits.
- **🛡️ Secure Sandboxing:** Uses Docker to build and run code safely, avoiding any local machine side-effects during testing.
- **📂 Zero Placeholders:** The Coder is instructed strictly to provide full implementation.
- **🚢 Zero-Config Deployment:** Ready to run natively via Python or 24/7 within a Docker Compose container.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (optional, but highly recommended for sandboxing)
- [Anthropic API key](https://console.anthropic.com)
- Telegram bot token from [@BotFather](https://t.me/BotFather)

### 2. Installation Setup
Clone the repository and install the dependencies:
```bash
git clone https://github.com/BinaryBard27/Agent_Factory.git
cd Agent_Factory

# Install dependencies
pip install -r requirements.txt

# Start from the configuration template
cp .env.example .env
```
*(Don't forget to fill in `.env` with your API keys!)*

### 3. Connect Telegram
To let the Liaison message your phone directly, you'll need your Chat ID. Message [@userinfobot](https://t.me/userinfobot) on Telegram, and it will reply with your ID. Add this into your `.env` file.

### 4. Run the Factory

**Option A — 🤖 Background Telegram Bot (Recommended)**
```bash
python main.py bot
```
*Leave this running in the background. Message your bot anytime to start a job!*

**Option B — 💻 Direct CLI Usage**
```bash
python main.py build "build a CLI tool that fetches BTC and ETH prices"
```

**Option C — 🐳 Docker Compose (24/7 Uptime Mode)**
```bash
docker-compose up -d
```

---

## 💬 Interacting with the Bot

| Command | Action |
| --- | --- |
| `/build <task>` | Start a new software build job. |
| `/status` | See the current progress of all active jobs. |
| `/resume <task>` | Resume a stopped/crashed job. |
| `/cancel <task>` | Clear state for a job and cancel it. |
| `/help` | Show all available commands. |

> **Pro Tip:** Simply send a standard text message with your idea, and the bot will automatically treat it as a `/build` request!

---

## 💡 Example Tasks

Need inspiration? Try sending these prompts:
- *"Build a CLI crypto price tracker for BTC and ETH with 24h percentage changes."*
- *"Write a Python script that monitors my Downloads folder and categorizes files by date."*
- *"Build a web scraper that pulls daily top headlines from Hacker News and exports them to a CSV."*
- *"Create a beautiful, terminal-based Pomodoro timer app with pausing and logging."*

---

## 📂 Architecture & Project Structure

Our core agents live in the `core/` directory and work sequentially:

```text
├── main.py                  ← Entry point (bot / CLI)
├── config/                  ← Configuration management (.env parsing)
├── core/
│   ├── orchestrator.py      ← Factory workflow loop driver
│   ├── architect.py         ← Agent 1: Spec Planning
│   ├── coder.py             ← Agent 2: Code Synthesis
│   ├── auditor.py           ← Agent 3: QA & Verification
│   └── logger.py            ← Unified robust logging
├── bots/                    ← Bot interfaces (Telegram built-in)
├── liaison/                 ← File shipping & system notifications
├── state/                   ← Bulletproof JSON state checkpoints
├── factory_jobs/            ← Finished, zipped projects land here
├── factory_state/           ← Hidden checkpoint progress trackers
└── docker-compose.yml       ← Full infrastructure deployment
```

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Requirement | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Your Anthropic key for the Claude LLM engine. |
| `TELEGRAM_BOT_TOKEN` | required | Used for receiving messages (from @BotFather). |
| `TELEGRAM_CHAT_ID` | required | Your personal ID, so nobody else can message your bot. |
| `MODEL` | optional | Default: `claude-opus-4-5` or similar. Adjust for speed/cost. |
| `MAX_RETRIES` | optional | Max loop iterations between Coder ↔️ Auditor (Default: `6`). |
| `USE_DOCKER` | optional | True/False. Run generated code in a secure Docker sandbox. |
| `SANDBOX_TIMEOUT` | optional | Seconds before force-killing a rogue script (Default: `60`). |

---

## 🤝 Contributing
Contributions, opened issues, and pull requests are welcome! If you devise a new Agent (`Security Reviewer`, `UI/UX Designer`), feel free to open a PR.

> **Warning:** Generated apps run best when `USE_DOCKER=true` is set. The internal Auditor agent leverages Docker to natively test scripts without installing dependencies on your host machine.
