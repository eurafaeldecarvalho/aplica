---
description: Show Aplica's state — today's applications, the day's report, stuck jobs and to-dos.
argument-hint: "[YYYY-MM-DD optional]"
---

Show Aplica's current state using the database (read-only). Run, for the date `$ARGUMENTS` (or today):

- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py today` — the day's applications (APPLICATIONS_COUNTED excludes uncertain).
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py report` — markdown summary (applications, log, blocked sites, questions, stuck jobs, "Needs you").
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py stuck list` and `todo list` — what is left for the user to finish by hand.
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py metrics` — funnel and reply/interview rate per source and per résumé variant.
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py followups --days 7` — applications with no reply for 7+ days (follow-up candidates).

Summarize for the user: how many applications, the rate per source, which résumé variant is doing best, what is stuck, what needs their action, and which jobs are due a follow-up.
