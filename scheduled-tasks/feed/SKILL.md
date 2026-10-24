---
name: aplica-feed
description: Rotina Aplica — rola o feed do LinkedIn em busca de vagas em posts; candidata por link e (só se o config permitir) faz ações sociais dentro dos tetos. ORQUESTRADOR.
---

# Rotina Aplica: feed — ORQUESTRADOR

Só roda se `config.behavior.feed_mode != "off"`. **Leia:** `common-rules` (§4 LinkedIn, tetos sociais) + `config.json`; subagente lê `apply-engine` (seção "Feed do LinkedIn") + `profile.json`.

⚠️ **Ações sociais são o maior vetor de bloqueio do LinkedIn (risco de CONTA).** Respeite `behavior.feed_mode` e `behavior.social.*`: em `apply_only`, só candidatura por link (curtir/comentar/conectar/DM viram rascunho, não envia). Em `full`, social dentro de `caps.social_per_day`, com cadência irregular, parando na hora em qualquer bloqueio. **Checar `JOBDB social-hoje` antes de cada ação social.**

## Passo 0
1. `JOBDB check` → OK. 2. `JOBDB linkedin-status` → `BLOQUEADO` → encerre. 3. `JOBDB lock adquirir --dono feed`.

## Execução (um subagente, ~20 min)
Rolar o feed e buscar posts de vaga (termos de `target.titles_search` + hashtags de contratação), últimas 24h. Sinais: "we're hiring", "looking for", "DM me", "link in comments", "apply here" — ler os comentários. Ao achar vaga: mesmo funil (gate de fit + geografia + dedup) e seguir exatamente o que o post pede para se candidatar (link/ATS; e-mail com CV se `email_resume`; cadastro; ou comentário/DM só se o social estiver ligado). 🛑 Qualquer CAPTCHA/bloqueio → parar o LinkedIn na hora.

## Encerramento
`JOBDB log --tipo feed` → limpeza do grupo de abas → `lock liberar` → "execução concluída — motivo: ...".
