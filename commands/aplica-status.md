---
description: Mostra o estado do Aplica — candidaturas de hoje, relatório do dia, vagas travadas e pendências.
argument-hint: "[AAAA-MM-DD opcional]"
---

Mostre o estado atual do Aplica usando o banco (somente leitura). Rode, na data `$ARGUMENTS` (ou hoje):

- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py hoje` — candidaturas do dia (CANDIDATURAS_CONTAM exclui incertas).
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py relatorio` — resumo em markdown (candidaturas, log, sites bloqueados, perguntas, vagas travadas, "Precisa de você").
- `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py travada list` e `pendencia list` — o que ficou para o usuário terminar na mão.

Resuma para o usuário: quantas candidaturas, taxa por fonte se der, o que está travado e o que precisa da ação dele.
