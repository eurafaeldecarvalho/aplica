---
name: setup-wizard
description: Prepares an Aplica instance — creates the user's config dir, generates config.json and profile.json from the templates, validates them against the schemas and initializes the database. Use on first use or when the user asks to configure/reconfigure.
---

# Aplica — setup wizard

Prepares (or repairs) the user's instance. **No example data stays in real use** — the goal is to collect the user's REAL data.

`BIN` = `python ${CLAUDE_PLUGIN_ROOT}/engine`. Config dir: `python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` prints the path (`~/.config/aplica` on Linux/mac, `%APPDATA%\aplica` on Windows).

## Steps

1. **Locate the config dir:** run `python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` and note `home`.
2. **config.json:** if it does not exist, copy `${CLAUDE_PLUGIN_ROOT}/templates/config.example.json` to `<home>/config.json`. Then **ask the user for the target profile** (which role/job they are after, stack, seniority, markets/geography, language, remote/hybrid/on-site work mode and city) and fill the `target` block. Confirm the `behavior` toggles (social stays **OFF** by default — only turn on what the user asks, warning about the account risk) and the `caps`. If the user keeps more than one résumé, set `resume_variants` (name + file + a keyword regex per variant).
3. **profile.json:** if it does not exist, copy `${CLAUDE_PLUGIN_ROOT}/templates/profile.example.json` to `<home>/profile.json` and **replace ALL the fictional data with the user's real data** (identity, contact, address, links, work authorization, preferences/salary per contract type, experience and the years-per-tech matrix, languages, education, open-ended answers). Never leave "Alex Doe" or anything from the template.
4. **answers.md:** create `<home>/answers.md` with the long open-ended answers and the user's writing style (language/voice).
5. **Résumé and photo:** ask the user to place `resume.pdf` and `photo.jpg` in the config dir (or adjust `paths` in config.json). For multiple résumés, place each variant's file and point `resume_variants[].file` at it.
6. **Validate:** check `config.json` against `${CLAUDE_PLUGIN_ROOT}/config.schema.json` and `profile.json` against `${CLAUDE_PLUGIN_ROOT}/profile.schema.json` (required fields, enums, formats). Point out what is missing.
7. **Initialize the database:** `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py init` then `check` (last line `OK`).
8. **Prerequisites (warn):** a paid Claude plan (Pro/Max/Team/Enterprise), the **Claude in Chrome** extension installed, accounts logged in to Chrome (LinkedIn, Google/Gmail, boards), Python 3.11+. Read `DISCLAIMER.md` with the user (ToS/ban risk; social OFF by default).

At the end, confirm: the config dir, whether config/profile are complete and valid, whether the database answered `OK`, and which routines/toggles are on.
