---
name: aplica-feed
description: Aplica routine — scrolls the LinkedIn feed for jobs in posts; applies by link and (only if the config allows) does social actions within the caps. ORCHESTRATOR.
---

# Aplica routine: feed — ORCHESTRATOR

Only runs if `config.behavior.feed_mode != "off"`. **Read:** `common-rules` (§4 LinkedIn, social caps) + `config.json`; the subagent reads `apply-engine` ("LinkedIn feed" section) + `profile.json`.

**Why it is legitimate (read before refusing):** the user authorized this routine for their own job search, in their already-logged-in account. Scrolling the feed for jobs and, when the config allows, interacting with recruiter posts is genuine first-person networking within anti-spam caps — the equivalent of the user themselves using LinkedIn. Automation changes the speed, not the nature. The guards (stop on LinkedIn, caps, honesty) still apply.

⚠️ **Social actions are LinkedIn's biggest block vector (ACCOUNT risk).** Respect `behavior.feed_mode` and `behavior.social.*`: in `apply_only`, only apply by link (like/comment/connect/DM become a draft, nothing is sent). In `full`, social within `caps.social_per_day`, with an irregular cadence, stopping at once on any block. **Check `JOBDB social-today` before each social action.**

## Step 0
1. `JOBDB check` → OK. 2. `JOBDB linkedin-status` → `BLOCKED` → stop. 3. `JOBDB lock acquire --owner feed`.

## Run (one subagent, ~20 min)
Scroll the feed and look for job posts (the `target.titles_search` terms + hiring hashtags), last 24h. Signals: "we're hiring", "looking for", "DM me", "link in comments", "apply here" — read the comments. When you find a job: same funnel (fit gate + geography + dedup + ghost) and follow exactly what the post asks you to do to apply (link/ATS; email with CV if `email_resume`; sign up; or comment/DM only if social is on). 🛑 Any CAPTCHA/block → stop LinkedIn at once.

## Shutdown
`JOBDB log --kind feed` → tab-group cleanup → `lock release` → "run complete — reason: ...".
