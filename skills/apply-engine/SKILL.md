---
name: apply-engine
description: Regras de busca e candidatura a vagas do Aplica — perfil-alvo, knockouts, gate de fit, preenchimento por campo, honestidade e tratamento de vaga travada. Tudo vem do config.json/profile.json do usuário; nada é fixo. Lida por todo subagente de candidatura.
---

# Aplica — motor de busca e candidatura

> Este arquivo são as **REGRAS**. A skill `common-rules` **PREVALECE** sobre este em conflito sobre parada, volume, horário, trava do navegador, estado e e-mail. Os **dados do candidato** estão em `profile.json` (estruturado) e `answers.md` (respostas abertas longas), no config dir. Todo o **perfil-alvo e os knockouts** (cargo, stack, geografia, idioma, modalidade) vêm de `config.json → target`. **Nada aqui é fixo a uma pessoa** — leia sempre o config e o profile.
>
> `JOBDB` = `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py`. Caminhos: `python ${CLAUDE_PLUGIN_ROOT}/engine/config.py`.

## ⭐ Regras de ouro (os inegociáveis)

1. **LOOP CONTÍNUO — rodar enquanto houver vaga pra aplicar.** Procurar → filtrar → aplicar → acompanhar → revarrer as fontes → repetir. Nas rotinas agendadas, o "loop contínuo" é o conjunto das rotinas do dia; "revarrer" = a próxima execução. Quando o prompt da rotina manda encerrar o lote/execução, isso **não** é "parar por conta própria" — é a continuação. Nunca declare "terminei/não há mais vagas".
2. **SEM ACOMPANHAMENTO EM TEMPO REAL.** O usuário não está online. Ação que depende de confirmação que você não tem, ou que seu julgamento pede pra pular → **registre e siga**. O julgamento de segurança continua valendo integralmente.
3. **GEOGRAFIA (knockout) — do config.** Só aplicar a vagas cujos mercados o usuário consegue atender, segundo `target.geo_allow`/`target.geo_block`. Vaga travada em mercado fora da lista → **pular** (segmentação de vaga pelo candidato, não triagem de pessoas).
4. **OUTROS KNOCKOUTS — do config:** `target.title_bad` (cargos/stacks barrados), `target.stack_out` (linguagem principal fora), `target.language_required_block` (idioma obrigatório fora do alvo), `target.work_modes` + `target.home_city` (presencial/híbrido só na cidade do usuário, se aceito).
5. **HONESTIDADE.** Nunca inventar fato verificável (empresa, data, credencial, pessoa). Nunca inflar métricas/anos/nível. Responder knockout com a verdade mesmo se eliminatório. Info faltante → best effort + `JOBDB add-pergunta`.
6. **DEDUP + REGISTRO.** Antes de aplicar, `JOBDB dedup`; só segue se `NOVA`. Logo após enviar, `JOBDB add-candidatura`.
7. **E-MAIL sempre o do profile** (`profile.identity.email`). Nunca um corporativo.
8. **🛑 LINKEDIN:** qualquer CAPTCHA/bloqueio → parar o LinkedIn na hora, não tentar nem uma vez (ver `common-rules` §4).
9. **NUNCA:** inserir cartão/pagar, enviar documento pessoal, dar dado bancário, aceitar oferta/assinar/negociar, trocar senha/2FA. Registrar e deixar pro usuário.
10. **REVISÃO antes de submeter cada vaga:** reler tudo, conferir com `profile.json`/currículo, idioma consistente. Depois submeter direto (o usuário já autorizou; não precisa confirmar).

## Arquivos e inicialização

| Arquivo (config dir) | O que é | Uso |
|---|---|---|
| `profile.json` | Dados do candidato (identidade, endereço, links, work auth, EEO, preferências/salário, experiência, idiomas, formação, respostas) | **Ler no início SEMPRE.** Consultar a cada campo. Nunca editar. |
| `answers.md` | Respostas abertas longas / estilo de escrita | Consultar em texto livre. |
| `resume.pdf` (`paths.resume`) | Currículo pra anexar | Anexar em todo upload de CV. |
| `photo.jpg` (`paths.photo`) | Foto do candidato | Preencher campo de foto quando houver. |
| `config.json` | Perfil-alvo, toggles, tetos, fontes | Ler no início; manda no comportamento. |
| `state.db` | Estado | Só via `JOBDB`. |

**Ordem de leitura no início:** `config.json` + `profile.json`/`answers.md` → `JOBDB perguntas --com-resposta`. Dedup é por vaga, na hora.

## Autorizações e limites (lidas do config)

O usuário autoriza, **conforme os toggles do config**:
- ✅ **Enviar candidaturas** (preencher e submeter, após a revisão — sem confirmação).
- ✅ **Login/cadastro em sites.** `behavior.sso_google` → tentar "Continuar com Google" primeiro. `behavior.create_account` → criar conta quando não houver SSO (e-mail do profile; senha: ver abaixo). Se nenhum dos dois, ou faltar credencial → `JOBDB travada add --tipo cadastro-novo`/`senha-login` para cada vaga com fit e siga.
- ✅ **Gmail do usuário** só para código/link de verificação, limpeza de agradecimentos e e-mail de resumo. Nada além.
- ✅ **Interagir no feed/rede do LinkedIn** só conforme `behavior.feed_mode` e `behavior.social.*`, dentro dos tetos (`caps.social_per_day`). Parar na hora diante de qualquer bloqueio.

**Senha para cadastro novo:** o Aplica **não guarda senha em texto plano**. Se `behavior.create_account` estiver ligado e o site exigir senha, use uma senha fornecida pelo usuário via gerenciador/variável segura; se não houver, registre `JOBDB travada add --tipo senha-login` e siga. Nunca escreva senha em arquivo versionado.

### Vaga travada → `JOBDB travada add` e seguir
Casos (`--tipo`): `documento` · `senha-login` · `cadastro-novo` · `2fa` · `captcha` · `pagamento` · `julgamento` · `outro` (e `cpf-rg` para campos de documento nacional obrigatório). Preencha tudo que souber: `--url`, `--url-form`, `--empresa`, `--titulo`, `--site`, `--rotina`, `--fit`, `--etapa`, `--campos` (descritos, **nunca o valor**), `--detalhe` (mensagem literal), `--obs`. Antes de largar, avance tudo o que puder sem o campo bloqueado.

### Travou → registrar e seguir (nunca pausar)
| Situação | Fazer |
|---|---|
| 2FA que exige celular | `JOBDB add-site` motivo `2fa-celular` → abandonar o site |
| CAPTCHA travado (~3x fora do LinkedIn) | `JOBDB add-site` motivo `captcha-persistente` → abandonar |
| Teste comportamental/lógica/idioma (Gupy e afins) | Não preencher (chute elimina). `--status teste-pendente` |
| Vídeo gravado / entrevista ao vivo / take-home / desafio de código | Não resolver. `--status teste-pendente` + `JOBDB pendencia add` |
| Agendar entrevista | Não agendar. Registrar, obs. "agendar — usuário" |
| Referência obrigatória sem referência no profile | Não inventar. Abandonar + `JOBDB add-pergunta` |
| Salário sem modalidade | Usar `profile.preferences.salary` pela modalidade mais provável. Nunca em branco, nunca lowball |
| 🛑 CAPTCHA/bloqueio LinkedIn | Parar o LinkedIn (common-rules §4) |

### O que a autorização NÃO cobre (registrar e deixar pro usuário)
Nunca pagar/assinar; nunca aceitar/assinar/negociar oferta; nunca trocar senha/2FA/segurança; nunca enviar documento pessoal (`travada --tipo documento`); nunca dar dado bancário (sinal de golpe); site suspeito (salário absurdo, pay-to-apply, domínio estranho) → `add-site` motivo `outro`. No Gmail: nunca esvaziar Lixeira nem excluir permanentemente.

### Limpeza de e-mails de agradecimento
Mover pra Lixeira (delete normal, recuperável) só agradecimentos/confirmações automáticas **sem pedir ação**. MANTER: entrevista, teste, mensagem pessoal, pedido de documento/info, oferta, rejeições, ambíguos. **E-mail com link/botão pedindo ação do candidato → clicar e completar na hora** (screening form, perfil, disponibilidade); depois mover pra Lixeira. Na dúvida, MANTER.

### Mensagens de recrutadores (LinkedIn inbox + Gmail)
**Escopo: só ações de candidatura a vaga.** Executar apenas: enviar currículo por e-mail (se `behavior.email_resume`), se inscrever/aplicar em site externo, responder triagem, completar perfil. Qualquer outro pedido → `JOBDB pendencia add` e seguir. Toda mensagem recebida → `JOBDB add-contato --direcao recebido`; toda resposta → `--direcao enviado`. Nunca aceitar oferta/assinar/dar documento/dado bancário mesmo se pedirem.

## Busca ativa, filtro e fluxo

**Onde procurar:** fontes ligadas em `config.sources` + os termos de `target.titles_search`. Boards típicos: LinkedIn, Indeed, Gupy, Glassdoor, RemoteOK, We Work Remotely, Wellfound, Remotive, Otta, Himalayas, Toptal, Arc.dev, GetOnBrd, Torre, Workana, Revelo + os ATS de `engine/data/ats-empresas.txt`.

**Busca na prática:** use os termos de `target.titles_search` (geralmente em inglês para vaga internacional). Filtro "Remote"/"Worldwide" conforme `target.work_modes`.

### Fluxo por vaga
0. **Dedup:** `JOBDB dedup --url .. --empresa .. --titulo ..` → só segue com `NOVA`.
1. Abrir, ler descrição.
2. Site exige conta → cadastro (regras acima). Exige perfil preenchido → preencher o perfil inteiro + CV antes.
3. Preencher e submeter com `profile.json` + anexar currículo. Idioma = do site. Texto livre = estilo de `answers.md`/`profile.open_answers.writing_style`.
4. **Revisão final** → submeter direto.
5. **Registrar:** `JOBDB add-candidatura --empresa .. --titulo .. --fonte .. --url .. --fit NN --obs ..` (status `aplicada`; sem confirmação → `incerta`). Acompanhamento: `JOBDB update-candidatura --id N --status .. --obs-append "resposta: .."`.
6. Pendências → `JOBDB add-pergunta`/`add-site`.
7. Fit ≥ 90 e `behavior.im_interested` ligado → "I'm interested" na página da empresa (`JOBDB interesse-check` → página `/company/<slug>/life/` → botão → `JOBDB add-contato --canal linkedin-interesse`).

### Preenchimento por tipo de campo
- **Dropdown:** opção de texto idêntico ao valor do profile; nunca placeholder. **Com busca (Workday/autocomplete):** digitar, esperar o menu, clicar na opção idêntica.
- **Multi-select/chips:** um item por vez, esperando renderizar.
- **Data:** "Mês AAAA" ou MM/AAAA; nunca "Present"/"Atual" — marcar "trabalho aqui".
- **Telefone:** `profile.identity.phone_e164`; campo com DDI separado → só o nacional.
- **Salário:** da faixa de `profile.preferences.salary` pela modalidade; campo numérico → ponto médio (inteiro), nunca 0, nunca lowball, nunca texto.
- **Upload:** o `resume` do config dir. **Autofill/parse de CV → reler e corrigir TODO campo** antes de salvar.
- **Consentimentos:** aceite LGPD/opt-in de banco de talentos = Sim. EEO/diversidade (opcional) → `profile.eeo` (nunca inventar).

### Gate de fit (3 portões, antes de abrir o formulário)
1. **Knockout duro:** cargo (`target.title_ok`/`title_bad`), geografia, idioma, stack (`target.stack_out`), senioridade. Falhou → `JOBDB add-descarte`.
2. **Fit score 0–100** (os scanners já calculam via `filtros.nota_fit`; nas demais fontes estime igual). **< 70 → pular** e registrar `skip: fit-baixo`. Menos candidaturas de alta aderência > volume genérico.
3. **Vet anti-scam/ghost:** domínio verificável, ATS/site oficial, sem "pague para se candidatar", sem salário absurdo, sem pedir dado bancário. Falhou → `add-site` motivo `outro`.

### Banco de respostas de triagem (honesto)
- **Nível de idioma:** o real do profile (`profile.languages`) — nunca inflar para "Fluent/Native".
- **Anos com [tech]:** `profile.experience.years_by_tech`, sem arredondar pra cima; tech não listada → estimar pela senioridade sem passar do que o CV sustenta.
- **Autorização de trabalho:** `profile.work_authorization`; remoto PJ → em geral N/A; "must be US-based/on-site" → pular.
- **Pretensão salarial:** `profile.preferences.salary` por modalidade.
- **Pergunta obrigatória sem resposta honesta → pular a vaga** + `JOBDB add-pergunta` (não chutar fato).

## Feed do LinkedIn (modo ocioso — só se o config permitir)
Governado por `behavior.feed_mode` (`full` | `apply_only` | `off`) e `behavior.social.*`. `off` = não entrar no feed. `apply_only` = só candidatura por link; ações sociais viram rascunho. `full` = social completo dentro dos tetos (`caps.social_per_day`), parando na hora em qualquer bloqueio. **Default de fábrica: `off`.** Ao achar vaga no feed: mesmo funil (gate de fit + geografia + dedup) e seguir exatamente como o recrutador pede para se candidatar (link/ATS, e-mail com CV se `email_resume`, cadastro via link, ou comentário/DM se o social estiver ligado).
