# Aplica (desktop app)

**The cockpit for Aplica — a point-and-click desktop app for the auto-apply job search plugin for Claude Code. Windows + Linux.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Electron](https://img.shields.io/badge/Electron-31-47848F.svg)](https://www.electronjs.org/)
[![platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux-blue.svg)](#install)

Aplica app is the friendly front-end for the **[aplica](https://github.com/eurafaeldecarvalho/aplica)** plugin. It gives you onboarding, a form for your data, toggles for every behavior, a schedule, and a live dashboard — no terminal required. The plugin is the engine; this app is the cockpit. They share one config directory (`~/.config/aplica` / `%APPDATA%\aplica`); nothing personal is stored in either repo.

> ⚠️ Read [`DISCLAIMER.md`](DISCLAIMER.md). Job boards restrict automation and your account can be limited or banned. Social actions are **off by default**. You run this on your own account, at your own risk.

## What you get

- **Home** — prerequisite checks with one-click install helpers (Python, Claude Code CLI), Claude in Chrome detection + install button, résumé/photo picker, and the disclaimer. The local database is created automatically on first launch (bundled engine, isolated per app — it never points at an existing DB on your machine).
- **Settings** (one modal, all config):
  - *Your data* — your real data (identity, links, work authorization, salary by modality, experience, years-per-tech, languages, education) plus the common application questions answered in your own voice. Writes `profile.json` / `answers.md`.
  - *Job preferences* — titles, stack, geography, company blocklist, language, work modes, sources. Writes `config.json → target`.
  - *Behavior* — every toggle (comment, connect, DM, like, "I'm interested", email résumé/summary, SSO, create account) plus daily caps, cadence and active hours. Social defaults off.
  - *Schedule* — times for each routine; run `/aplica-schedule` in Claude Code to turn them into real scheduled tasks.
- **Dashboard** — applications, response rate by source, follow-ups, stuck jobs and to-dos, read live from your local database.
- **Run** — run a round now via `claude -p`, autonomous, with live output and a Stop button.

## Windows SmartScreen ("unknown publisher")

The installer isn't code-signed yet, so Windows Defender SmartScreen shows *"Windows protected your PC / unknown publisher"*. This is expected for a new, unsigned app — it's not a virus warning. Click **More info → Run anyway** to install. (Removing the prompt permanently requires a paid code-signing certificate; that's on the roadmap.)

## Requirements

- A **paid Claude plan** and the **Claude in Chrome** extension, with your accounts logged in.
- **Python 3.11+** and the **Claude Code CLI** (`claude`) on your PATH.
- The **[aplica](https://github.com/eurafaeldecarvalho/aplica)** plugin installed in Claude Code (`/plugin marketplace add eurafaeldecarvalho/aplica` → `/plugin install aplica`).

## Install

Download the installer for your OS from [Releases](https://github.com/eurafaeldecarvalho/aplica-app/releases):

- **Windows** — `Aplica-Setup-<version>.exe`
- **Linux** — `Aplica-<version>.AppImage` or the `.deb`

## Build from source

```bash
npm install
npm run dev     # run in development
npm run dist    # build installers for the current OS (dist/)
```

The Python engine is vendored under `engine/` and bundled into the app for local database reads; the agentic runs use the installed `aplica` plugin via `claude -p`. Keep `engine/` in sync with the plugin repo.

## License

MIT © Rafael de Carvalho. Built for [Claude Code](https://claude.com/claude-code); not affiliated with Anthropic.
