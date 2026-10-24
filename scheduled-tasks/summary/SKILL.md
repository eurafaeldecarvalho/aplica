---
name: aplica-summary
description: Rotina Aplica — monta o resumo do dia (candidaturas, travadas, pendências) e, se o usuário quiser, envia por e-mail para ele mesmo. ORQUESTRADOR.
---

# Rotina Aplica: summary — ORQUESTRADOR

Resumo diário. **Leia:** `common-rules` + `config.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

## Passos
1. `JOBDB check` → OK.
2. `JOBDB backup` (cópia consistente do dia).
3. `JOBDB relatorio` → corpo do resumo em markdown (candidaturas do dia, log, sites bloqueados, perguntas novas, vagas travadas, "Precisa de você").
4. `JOBDB export` → atualiza `visao/*.md` legíveis no config dir.
5. **E-mail (opcional):** só se `config.behavior.email_summary` for `true`, abra o Gmail (navegador isolado, common-rules §5 e técnica do corpo §7) e envie o relatório para `profile.identity.email` (o próprio usuário). Caso contrário, só deixe o relatório/export prontos. Nunca envie para outro endereço.
6. `JOBDB log --tipo summary --texto "resumo gerado"` → "execução concluída — motivo: ...".

Nunca envie dado do usuário para fora a não ser o resumo para o próprio e-mail dele.
