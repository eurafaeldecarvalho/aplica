---
name: setup-wizard
description: Prepara uma instância do Aplica — cria o config dir do usuário, gera config.json e profile.json a partir dos templates, valida contra os schemas e inicializa o banco. Use no primeiro uso ou quando o usuário pedir para configurar/reconfigurar.
---

# Aplica — assistente de configuração

Prepara (ou conserta) a instância do usuário. **Nada de dados de exemplo fica no uso real** — o objetivo é coletar os dados REAIS do usuário.

`BIN` = `python ${CLAUDE_PLUGIN_ROOT}/engine`. Config dir: `python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` mostra o caminho (`~/.config/aplica` no Linux/mac, `%APPDATA%\aplica` no Windows).

## Passos

1. **Localizar o config dir:** rode `python ${CLAUDE_PLUGIN_ROOT}/engine/config.py` e anote `home`.
2. **config.json:** se não existir, copie `${CLAUDE_PLUGIN_ROOT}/templates/config.example.json` para `<home>/config.json`. Depois **pergunte ao usuário o perfil-alvo** (qual cargo/vaga procura, stack, senioridade, mercados/geografia, idioma, modalidade remoto/híbrido/presencial e cidade) e preencha o bloco `target`. Confirme os toggles de `behavior` (social fica **OFF** por padrão — só ligue o que o usuário pedir, avisando do risco de conta) e os `caps`.
3. **profile.json:** se não existir, copie `${CLAUDE_PLUGIN_ROOT}/templates/profile.example.json` para `<home>/profile.json` e **troque TODOS os dados fictícios pelos dados reais do usuário** (identidade, contato, endereço, links, autorização de trabalho, preferências/salário por modalidade, experiência e matriz de anos por tech, idiomas, formação, respostas abertas). Nunca deixe "Alex Doe" nem nada do template.
4. **answers.md:** crie `<home>/answers.md` com as respostas abertas longas e o estilo de escrita do usuário (idioma/voz).
5. **Currículo e foto:** peça ao usuário para colocar `resume.pdf` e `photo.jpg` no config dir (ou ajuste `paths` no config.json).
6. **Validar:** confira `config.json` contra `${CLAUDE_PLUGIN_ROOT}/config.schema.json` e `profile.json` contra `${CLAUDE_PLUGIN_ROOT}/profile.schema.json` (campos obrigatórios, enums, formatos). Aponte o que faltar.
7. **Inicializar o banco:** `python ${CLAUDE_PLUGIN_ROOT}/engine/jobdb.py init` e depois `check` (última linha `OK`).
8. **Pré-requisitos (avisar):** plano Claude pago (Pro/Max/Team/Enterprise), extensão **Claude in Chrome** instalada, contas logadas no Chrome (LinkedIn, Google/Gmail, boards), Python 3.11+. Leia o `DISCLAIMER.md` com o usuário (risco de ToS/ban; social OFF por padrão).

Ao final, confirme: config dir, se config/profile estão completos e válidos, se o banco respondeu `OK`, e quais rotinas/toggles estão ligados.
