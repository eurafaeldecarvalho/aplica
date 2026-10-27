---
description: Create/update the Aplica routines' scheduled tasks from config.schedule (times set in the app).
---

Read the Aplica config dir's `config.json` (`python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` prints the path) and materialize the `schedule` block as real scheduled tasks, using Claude Code's scheduled-tasks tool (`mcp__scheduled-tasks__*`).

For each routine in `config.schedule` (`ats`, `linkedin_jobs`, `recruiters`, `feed`, `summary`):
- If `enabled: false` → **remove** the matching scheduled task if it exists (`delete_scheduled_task`) and move on.
- If `enabled: true` → for each time in `times` (HH:MM), **create or update** a scheduled task (`create_scheduled_task`/`update_scheduled_task`) that, at that time, runs the matching routine — the task body should tell the agent to follow the template in `${CLAUDE_PLUGIN_ROOT}/scheduled-tasks/<routine>/SKILL.md` (e.g. `ats` → `scheduled-tasks/ats-boards`, `linkedin_jobs` → `scheduled-tasks/linkedin-jobs`, `recruiters`, `feed`, `summary`). Convert HH:MM into the scheduling format the tool expects (a daily cron at that time).

Name the tasks stably (e.g. `aplica-<routine>-<HH><MM>`) so you can reconcile on future runs: list the existing ones (`list_scheduled_tasks`), create the missing ones, update those whose time changed, and remove those no longer in the config (or whose routine was turned off). Never duplicate.

Respect the toggles: only schedule `feed` if `behavior.feed_mode != off`. At the end, list for the user what was scheduled (routine, times) and what was removed.
