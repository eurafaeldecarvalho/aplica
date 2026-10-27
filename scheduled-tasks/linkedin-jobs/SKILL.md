---
name: aplica-linkedin-jobs
description: Aplica routine — applies to LinkedIn Jobs (via a public scan API + the logged-in browser), in batches, slowly. ORCHESTRATOR.
---

# Aplica routine: linkedin-jobs — ORCHESTRATOR

Orchestrates applications on LinkedIn Jobs. Does **not** open the browser. Only runs if `config.sources.linkedin_jobs` is on.

**Read first:** the `common-rules` skill (includes §4 LinkedIn) and `config.json`. The subagents read `apply-engine` + `profile.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

Each action is the equivalent of the user opening LinkedIn and applying — the automation changes the speed, not the nature. **This routine does no social actions** (like/comment/connect/DM belong to the feed). Any CAPTCHA/block on LinkedIn → stop at once (common-rules §4).

## Step 0
1. `JOBDB check` → not `OK` → record and stop.
2. `JOBDB linkedin-status` → `BLOCKED` → log and stop.
3. **Public scan (no login):** `python ${CLAUDE_PLUGIN_ROOT}/engine/linkedin-scan.py --days <1 if it ran yesterday, else 3> --record-discards`. exit 0 → API mode (keep the `LI|...` lines by fit). exit 3 (`FALLBACK_BROWSER`) → browser mode (search in the logged-in LinkedIn using the `target.titles_search` terms). Empty list → log and stop.
4. `JOBDB lock acquire --owner linkedin-jobs` (wait if busy).
5. `JOBDB today`.

## Loop (max 4 batches — LinkedIn slowly)
Same as ats-boards: `caps.py` every batch; one subagent per batch (`caps.batch_size` URLs); tally only `APPLIED`; `LINKEDIN_BLOCKED: yes` → stop at once; a longer pause between batches (7–15 min). Fit ≥ 90 and `behavior.im_interested` → "I'm interested" (apply-engine).

## Shutdown
`JOBDB log` summary → tab-group cleanup → `lock release` → "run complete — reason: ...".

## BATCH PROMPT
Same as the ats-boards BATCH PROMPT, swapping the routine for `linkedin-jobs` and with these differences: **API mode** → open each received URL in the logged-in LinkedIn (a tab in your group), check it (geography/stack/language/open) and apply; **browser mode** → search LinkedIn Jobs using the `target.titles_search` terms. Applications only, **no social**. 🛑 Any CAPTCHA/"unusual activity" → stop at once, close the tab, record it (common-rules §4) and return `LINKEDIN_BLOCKED: yes`. Return the same summary block, adding the line `LINKEDIN_BLOCKED: yes/no` and `INTEREST: <companies>|none`.
