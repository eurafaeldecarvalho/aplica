---
description: Roda uma rodada de candidaturas agora (argumento: ats | linkedin | freehire | recruiters | feed | all). Default all.
argument-hint: "[ats|linkedin|freehire|recruiters|feed|all]"
---

Rode uma rodada de candidaturas do Aplica **agora**, para a fonte `$ARGUMENTS` (default `all`).

Antes de tudo, leia as skills `common-rules` e `apply-engine`, e o `config.json`/`profile.json` do config dir. Confirme os pré-requisitos (health-check `jobdb.py check` = OK; `jobdb.py linkedin-status` se for mexer no LinkedIn). Respeite os toggles do `config.behavior` e os tetos de `config.caps` — **nunca** faça ação social se o config não permitir.

Você é o ORQUESTRADOR: não abre o navegador; adquire a trava (`jobdb.py lock adquirir --dono aplica-run`), dispara **um subagente por vez** (`general-purpose`, sonnet) por lote de `caps.batch_size`, checa `caps.py` a cada lote, e ao fim faz a limpeza do grupo de abas e libera a trava. Para a fonte escolhida, use o scanner correspondente quando houver (`ats-scan.py`, `linkedin-scan.py`, `freehire-scan.py`) para montar a fila por fit; `recruiters` = checar LinkedIn inbox + Gmail (seção "Mensagens de recrutadores"); `feed` = só se `behavior.feed_mode != off`.

Ao terminar: `jobdb.py log` com o resumo e "execução concluída — motivo: <...>". Nunca declare "não há mais vagas".
