---
description: Cria/atualiza as tarefas agendadas das rotinas do Aplica a partir de config.schedule (horários definidos no app).
---

Leia `config.json` do config dir do Aplica (`python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` mostra o caminho) e materialize o bloco `schedule` como tarefas agendadas reais, usando a ferramenta de tarefas agendadas do Claude Code (`mcp__scheduled-tasks__*`).

Para cada rotina em `config.schedule` (`ats`, `linkedin_jobs`, `recruiters`, `feed`, `summary`):
- Se `enabled: false` → **remova** a tarefa agendada correspondente se existir (`delete_scheduled_task`) e siga.
- Se `enabled: true` → para cada horário em `times` (HH:MM), **crie ou atualize** uma tarefa agendada (`create_scheduled_task`/`update_scheduled_task`) que, no horário, rode a rotina correspondente — o corpo da tarefa deve instruir o agente a seguir o template em `${CLAUDE_PLUGIN_ROOT}/scheduled-tasks/<rotina>/SKILL.md` (ex.: `ats` → `scheduled-tasks/ats-boards`, `linkedin_jobs` → `scheduled-tasks/linkedin-jobs`, `recruiters`, `feed`, `summary`). Converta HH:MM para o formato de agendamento que a ferramenta espera (cron diário naquele horário).

Nomeie as tarefas de forma estável (ex.: `aplica-<rotina>-<HH><MM>`) para poder reconciliar em execuções futuras: liste as existentes (`list_scheduled_tasks`), crie as que faltam, atualize as que mudaram de horário e remova as que não estão mais no config (ou cuja rotina foi desligada). Nunca duplique.

Respeite os toggles: só agende `feed` se `behavior.feed_mode != off`. Ao final, liste para o usuário o que ficou agendado (rotina, horários) e o que foi removido.
