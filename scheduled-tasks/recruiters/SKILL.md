---
name: aplica-recruiters
description: Rotina Aplica — checa mensagens de recrutadores (LinkedIn inbox + Gmail) e responde/aplica apenas no escopo de candidatura a vaga. ORQUESTRADOR.
---

# Rotina Aplica: recruiters — ORQUESTRADOR

Checa e responde recrutadores. Prioridade sobre nova candidatura. **Leia:** `common-rules` + `config.json`; subagente lê `apply-engine` (seção "Mensagens de recrutadores") + `profile.json`.

## Passo 0
1. `JOBDB check` → OK. 2. `JOBDB linkedin-status` (se for ao LinkedIn). 3. `JOBDB lock adquirir --dono recruiters`.

## Execução (um subagente)
Dispare um subagente com o PROMPT abaixo. Ele checa **ambos**: LinkedIn inbox (`linkedin.com/messaging`, não lidas/recentes) e Gmail do usuário. Escopo estrito: só ações de candidatura a vaga (aplicar em link externo; enviar currículo por e-mail **se `behavior.email_resume`**; responder triagem; completar perfil). Qualquer outro pedido → `JOBDB pendencia add` e seguir. Toda mensagem recebida → `JOBDB add-contato --direcao recebido`; resposta → `--direcao enviado`. Nunca aceitar oferta/assinar/dar documento/dado bancário. Entrevista/teste/vídeo → `update-candidatura --status teste-pendente` + `pendencia add`.

## Encerramento
`JOBDB log --tipo recruiters` → limpeza do grupo de abas → `lock liberar` → "execução concluída — motivo: ...".

## PROMPT (subagente)
> Você roda a rotina Aplica `recruiters`. Leia `common-rules`, `apply-engine` (seção "Mensagens de recrutadores") e `profile.json`/`config.json`. Navegador isolado (common-rules §5). Trava: só `JOBDB lock check --dono recruiters`. 🛑 CAPTCHA no LinkedIn → pare (common-rules §4). Devolva: RESPONDIDAS, APLICADAS, TESTE_PENDENTE, PENDENCIAS_NOVAS, PROBLEMAS.
