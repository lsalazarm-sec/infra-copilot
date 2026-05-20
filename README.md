<div align="center">

# infra-copilot

**Ask your infrastructure questions in plain English. Runs 100% locally on your GPU.**

[![CI](https://github.com/lsalazarm-sec/infra-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/lsalazarm-sec/infra-copilot/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ollama](https://img.shields.io/badge/Ollama-powered-purple.svg)](https://ollama.com)

[Demo](#demo) · [Features](#features) · [Quickstart](#quickstart) · [Architecture](#architecture) · [Safety](#safety-model)

</div>

---

## Why this exists

Debugging infrastructure at 2am means switching between 8 terminal tabs — kubectl,
journalctl, top, ss, logs — before you even start reasoning about what went wrong.

`infra-copilot` is a local LLM agent that does the data gathering for you. You ask a
question in plain English, it runs the right commands, reads the output, and explains
what it found. No data leaves your network — the LLM runs on your GPU via Ollama.

---

## Features

- **Local LLM** via [Ollama](https://ollama.com) — Qwen 2.5 Coder 14B or any model you choose
- **Real tool-calling** — the agent actually runs kubectl, journalctl, df, ps, and more
- **Safety-first** — read-only by default, strict command allowlist, no shell interpolation
- **Audit log** — every command logged to JSONL for postmortems
- **TUI + CLI** — interactive Textual UI or one-shot queries
- **AMD GPU support** — built and tested on RX 7700 XT with ROCm 7.x

---

## Quickstart

### Prerequisites

- Linux (Ubuntu 24.04 recommended)
- Python 3.12+
- [Ollama](https://ollama.com) running locally
- kubectl configured with at least one cluster

### Install

```bash
ollama pull qwen2.5-coder:14b

git clone https://github.com/lsalazarm-sec/infra-copilot.git
cd infra-copilot
uv sync
copilot init
```

### One-shot query

```bash
copilot ask "why is the api-gateway pod restarting?"
```

### Interactive TUI

```bash
copilot tui
```

---

## Architecture
User (CLI / TUI)
│
▼
Agent (PydanticAI)  ◄──►  Local LLM (Ollama / Qwen 2.5 Coder)
│
├── kubectl tool  ──►  Kubernetes cluster
├── shell tool    ──►  journalctl, df, ps, ss...
└── audit log     ──►  ~/.local/share/infra-copilot/audit.jsonl

See [docs/architecture.md](docs/architecture.md) for full design decisions.

---

## Safety model

| Guardrail | Default |
|---|---|
| Read-only mode | ON |
| kubectl allowed verbs | get, describe, logs, top, explain, version |
| Shell allowed binaries | journalctl, systemctl, ps, ss, df, free, uptime, ip |
| Audit log | Always on |
| No shell string interpolation | Always |

---

## Development

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check .
```

---

## License

MIT © Luis Salazar
