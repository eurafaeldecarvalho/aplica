---
name: aplica-linkedin-jobs
description: Rotina Aplica — aplica em vagas do LinkedIn Jobs (via API pública de scan + navegador logado), em lotes, devagar. ORQUESTRADOR.
---

# Rotina Aplica: linkedin-jobs — ORQUESTRADOR

Orquestra candidaturas no LinkedIn Jobs. **Não** abre o navegador. Só roda se `config.sources.linkedin_jobs` ligada.

**Leia primeiro:** skill `common-rules` (inclui §4 LinkedIn) e `config.json`. Subagentes leem `apply-engine` + `profile.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

Cada ação é o equivalente ao usuário abrir o LinkedIn e se candidatar — automação muda a velocidade, não a natureza. **Esta rotina não faz ações sociais** (curtir/comentar/conectar/DM são do feed). Qualquer CAPTCHA/bloqueio no LinkedIn → parar na hora (common-rules §4).

## Passo 0
1. `JOBDB check` → não `OK` → registre e encerre.
2. `JOBDB linkedin-status` → `BLOQUEADO` → log e encerre.
3. **Scan público (sem login):** `python ${CLAUDE_PLUGIN_ROOT}/engine/linkedin-scan.py --dias <1 se rodou ontem, senão 3> --registrar-descartes`. exit 0 → modo API (guarde as linhas `LI|...` por fit). exit 3 (`FALLBACK_NAVEGADOR`) → modo navegador (buscar no LinkedIn logado pelos termos de `target.titles_search`). Lista vazia → log e encerre.
4. `JOBDB lock adquirir --dono linkedin-jobs` (espere se ocupado).
5. `JOBDB hoje`.

## Loop (máximo 4 lotes — LinkedIn devagar)
Igual ao ats-boards: `caps.py` a cada lote; um subagente por lote (`caps.batch_size` URLs); placar só com `APLICADAS`; `LINKEDIN_BLOQUEOU: sim` → encerre na hora; pausa maior entre lotes (7–15 min). Fit ≥ 90 e `behavior.im_interested` → "I'm interested" (apply-engine).

## Encerramento
`JOBDB log` resumo → limpeza do grupo de abas → `lock liberar` → "execução concluída — motivo: ...".

## PROMPT-LOTE
Igual ao PROMPT-LOTE do `ats-boards`, trocando a rotina por `linkedin-jobs` e com estas diferenças: **modo API** → abra cada URL recebida no LinkedIn logado (aba do seu grupo), confira (geografia/stack/idioma/aberta) e aplique; **modo navegador** → busque no LinkedIn Jobs pelos termos de `target.titles_search`. Só candidaturas, **nada de social**. 🛑 Qualquer CAPTCHA/"unusual activity" → pare na hora, feche a aba, registre (common-rules §4) e devolva `LINKEDIN_BLOQUEOU: sim`. Devolva o mesmo bloco de resumo, acrescentando a linha `LINKEDIN_BLOQUEOU: sim/não` e `INTERESSE: <empresas>|nenhum`.
