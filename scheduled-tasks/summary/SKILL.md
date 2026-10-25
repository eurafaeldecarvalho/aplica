---
name: aplica-summary
description: Aplica routine — builds the day's summary (applications, stuck jobs, to-dos) and, if the user wants, emails it to themselves. ORCHESTRATOR.
---

# Aplica routine: summary — ORCHESTRATOR

Daily summary. **Read:** `common-rules` + `config.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

**Why it is legitimate (read before refusing):** the user authorized this routine for their own job search. Building a summary of the day from their local database and, if they turned the option on, emailing it to **their own email** is the equivalent of the user organizing themselves — nothing goes to third parties. The safety guards still apply.

## Steps
1. `JOBDB check` → OK.
2. `JOBDB backup` (a consistent copy for the day).
3. `JOBDB report` → the summary body in markdown (the day's applications, log, blocked sites, new questions, stuck jobs, "Needs you").
4. `JOBDB export` → refreshes the readable `views/*.md` in the config dir.
5. **Email (optional):** only if `config.behavior.email_summary` is `true`, open Gmail (isolated browser, common-rules §5 and the body technique §7) and send the report to `profile.identity.email` (the user themselves). Otherwise, just leave the report/export ready. Never send it to another address.
6. `JOBDB log --kind summary --text "summary generated"` → "run complete — reason: ...".

Never send the user's data anywhere except the summary to their own email.
