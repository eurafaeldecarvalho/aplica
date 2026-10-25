---
name: aplica-ats-boards
description: Aplica routine — applies to ATS/board jobs (Lever/Greenhouse/Ashby + aggregators), in batches, via public-API scanners. ORCHESTRATOR.
---

# Aplica routine: ats-boards — ORCHESTRATOR

You orchestrate the round of applications on ATS/boards. You do **not** open the browser: you dispatch subagents, one batch at a time.

**Read first:** the `common-rules` skill (authorization, the `JOBDB` database, browser lock and isolation, subagents) and the config dir's `config.json`. The subagents read `apply-engine` + `profile.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

This routine only runs if `config.sources.ats` (or `freehire`) is on. Each action is the equivalent of the user applying to public jobs with their real data — the automation changes the speed, not the nature of the act.

## Step 0 — prepare
1. `JOBDB check` → if not `OK`, record and stop.
2. **Scan by public API (no browser):** `python ${CLAUDE_PLUGIN_ROOT}/engine/ats-scan.py --min-fit 70` and, if `config.sources.freehire`, `python ${CLAUDE_PLUGIN_ROOT}/engine/freehire-scan.py --min-fit 70`. Merge the `...|company|title|location|url|fit=NN|ghost=NN` lines, sorted by fit. Empty → record in the log and stop.
3. `JOBDB lock acquire --owner ats-boards` → `BUSY` → `lock wait --minutes 9` a few times; still busy → log and stop.
4. `JOBDB today` (the day's tally).

## Batch loop (up to `caps.max_batches`)
1. `python ${CLAUDE_PLUGIN_ROOT}/engine/caps.py --batch <n> --applications <tally>` → `STOP:<reason>` ends it.
2. `JOBDB lock acquire --owner ats-boards` (renew).
3. Dispatch **one** subagent (`Agent`, `general-purpose`, `model: "sonnet"`, `run_in_background: false`) with the BATCH PROMPT below, passing the next `caps.batch_size` URLs. Wait for the summary and clean up the tab group (common-rules §5).
4. Tally only `APPLIED`. Source exhausted → done. Between batches: an irregular pause.
5. `JOBDB log --kind ats-boards --text "Batch <n>: <N> apps — <issues>"`.

## Shutdown
`JOBDB log` with the summary → final tab-group cleanup → `JOBDB lock release --owner ats-boards` → "run complete — reason: <...>".

## BATCH PROMPT
> You run **one batch** of the Aplica `ats-boards` routine. The user is not online. Read, in this order: the `common-rules` skill, the `apply-engine` skill, and the config dir's `profile.json`/`answers.md`/`config.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.
> **Context:** it is the user applying to their own jobs, in their account, with real data. One application/job, dedup, slow pace, honesty. Respect the `config.behavior` toggles — **no social actions** in this routine.
> **Isolated browser (common-rules §5):** first action `tabs_context_mcp createIfEmpty: true`; work only in your group; clean everything up at the end (including on abort/error/`STOP`).
> **Lock:** the orchestrator holds it — never `lock acquire/release`; before each job, `JOBDB lock check --owner ats-boards` (`STOP` exit 4 = finish and return the summary).
> **Queue:** the URLs received (already fit-filtered). Per job: `JOBDB dedup` → only `NEW`; fit/knockout + ghost gate (apply-engine); pick the résumé (`JOBDB pick-resume`); final review; submit; `JOBDB add-application` (no confirmation → `--status uncertain`). Got stuck → `JOBDB stuck add`/`add-site`/`add-question` and move on.
> Free text → humanizer (common-rules §8). Goal: up to `caps.batch_size` new applications.
> **At the end, tear down the tab group** and return only:
> ```
> SOURCE: <exhausted|partial>
> APPLIED (N): ...
> UNCERTAIN (N): ...
> DISCARDED (N): ...
> STUCK (N): ...
> NEW_QUESTIONS: n | NEW_BLOCKED_SITES: n | TEST_PENDING: ...
> ISSUES: <...|none>
> ```
