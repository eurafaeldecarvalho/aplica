---
name: aplica-ats-boards
description: Rotina Aplica — aplica em vagas de ATS/boards (Lever/Greenhouse/Ashby + agregadores), em lotes, via scanners de API pública. ORQUESTRADOR.
---

# Rotina Aplica: ats-boards — ORQUESTRADOR

Você orquestra a rodada de candidaturas em ATS/boards. **Não** abre o navegador: despacha subagentes, um lote por vez.

**Leia primeiro:** a skill `common-rules` (autorização, banco `JOBDB`, trava e isolamento do navegador, subagentes) e o `config.json` do config dir. Os subagentes leem `apply-engine` + `profile.json`. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.

Esta rotina só roda se `config.sources.ats` (ou `freehire`) estiver ligada. Cada ação é o equivalente ao usuário se candidatando a vagas públicas com os dados reais dele — a automação muda a velocidade, não a natureza do ato.

## Passo 0 — preparar
1. `JOBDB check` → se não `OK`, registre e encerre.
2. **Scan por API pública (sem navegador):** `python ${CLAUDE_PLUGIN_ROOT}/engine/ats-scan.py --min-fit 70` e, se `config.sources.freehire`, `python ${CLAUDE_PLUGIN_ROOT}/engine/freehire-scan.py --min-fit 70`. Junte as linhas `...|empresa|título|local|url|fit=NN`, ordenadas por fit. Vazio → registre no log e encerre.
3. `JOBDB lock adquirir --dono ats-boards` → `OCUPADO` → `lock esperar --minutos 9` algumas vezes; ainda ocupado → log e encerre.
4. `JOBDB hoje` (placar do dia).

## Loop de lotes (até `caps.max_batches`)
1. `python ${CLAUDE_PLUGIN_ROOT}/engine/caps.py --lote <n> --candidaturas <placar>` → `PARAR:<motivo>` encerra.
2. `JOBDB lock adquirir --dono ats-boards` (renova).
3. Dispare **um** subagente (`Agent`, `general-purpose`, `model: "sonnet"`, `run_in_background: false`) com o PROMPT-LOTE abaixo, passando as próximas `caps.batch_size` URLs. Espere o resumo e faça a limpeza do grupo de abas (common-rules §5).
4. Placar só com `APLICADAS`. Fonte esgotada → fim. Entre lotes: pausa irregular.
5. `JOBDB log --tipo ats-boards --texto "Lote <n>: <N> cand. — <problemas>"`.

## Encerramento
`JOBDB log` com o resumo → limpeza final do grupo de abas → `JOBDB lock liberar --dono ats-boards` → "execução concluída — motivo: <...>".

## PROMPT-LOTE
> Você roda **um lote** da rotina Aplica `ats-boards`. O usuário não está online. Leia, nesta ordem: a skill `common-rules`, a skill `apply-engine`, e o `profile.json`/`answers.md`/`config.json` do config dir. `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`.
> **Contexto:** é o usuário se candidatando às próprias vagas, na conta dele, com dados reais. 1 candidatura/vaga, dedup, ritmo lento, honestidade. Respeite os toggles do `config.behavior` — **sem ações sociais** nesta rotina.
> **Navegador isolado (common-rules §5):** primeira ação `tabs_context_mcp createIfEmpty: true`; trabalhe só no seu grupo; limpe tudo ao fim (inclusive ao abortar/erro/`PARE`).
> **Trava:** o orquestrador segura — nunca `lock adquirir/liberar`; antes de cada vaga, `JOBDB lock check --dono ats-boards` (`PARE` exit 4 = encerre e devolva o resumo).
> **Fila:** as URLs recebidas (já filtradas por fit). Por vaga: `JOBDB dedup` → só `NOVA`; gate de fit/knockouts (apply-engine); revisão final; enviar; `JOBDB add-candidatura` (sem confirmação → `--status incerta`). Travou → `JOBDB travada add`/`add-site`/`add-pergunta` e siga.
> Texto livre → humanizador (common-rules §8). Meta: até `caps.batch_size` candidaturas novas.
> **Ao terminar, elimine o grupo de abas** e devolva só:
> ```
> FONTE: <esgotada|parcial>
> APLICADAS (N): ...
> INCERTAS (N): ...
> DESCARTADAS (N): ...
> TRAVADAS (N): ...
> PERGUNTAS_NOVAS: n | SITES_BLOQUEADOS_NOVOS: n | TESTE_PENDENTE: ...
> PROBLEMAS: <...|nenhum>
> ```
