---
description: Configure (or reconfigure) the Aplica instance — create the config dir, config.json, profile.json and initialize the database.
---

Invoke the `setup-wizard` skill and walk the user through configuring Aplica: locate the config dir, fill `config.json` (target profile and toggles — social OFF by default), fill `profile.json` with the user's REAL data, create `answers.md`, place the résumé/photo (and any `resume_variants`), validate against the schemas and run `jobdb.py init` + `check`. Read `DISCLAIMER.md` with the user.
