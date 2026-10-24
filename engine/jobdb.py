#!/usr/bin/env python3
# Aplica — banco do motor de candidatura (SQLite). Única porta de escrita dos agentes:
# nunca editar o .db na mão. Caminhos, tetos e empregador atual vêm de config.py (config.json
# do usuário). Ajuda: python jobdb.py -h  |  python jobdb.py <comando> -h
import argparse, datetime, io, os, re, sqlite3, sys, unicodedata
import config

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DB = config.DB
BACKUPS = config.BACKUPS
KEEP_BACKUPS = 30
# Versão do schema do state.db. Carimbada na tabela `controle` no init e conferida no check —
# detecta drift se um banco criado por uma versão antiga do motor for aberto por uma mais nova.
SCHEMA_VERSION = "1"

STATUS_CAND = ("aplicada", "incerta", "teste-pendente", "em-processo", "entrevista",
               "rejeitada", "sem-retorno", "oferta", "desistiu")
MOTIVOS_SITE = ("linkedin-bloqueio", "2fa-celular", "captcha-persistente", "email-nao-chegou",
                "sso-google-indisponivel", "cadastro-rejeitado", "conta-ja-existe-senha-invalida",
                "bloqueio-regional", "site-fora-do-ar", "exige-documento", "paywall-assinatura", "outro")
STATUS_SITE = ("bloqueado", "resolvido", "descartado")
STATUS_PERG = ("pendente", "respondida", "migrada")
CANAIS = ("linkedin-dm", "linkedin-conexao", "linkedin-comentario", "linkedin-interesse", "email", "outro")
# Vaga que o agente não conseguiu terminar e o usuário termina na mão. Nunca guardar o VALOR de
# documento/senha — só que o campo existe.
TIPOS_TRAVADA = ("cpf-rg", "documento", "senha-login", "cadastro-novo", "2fa", "captcha", "pagamento", "julgamento", "outro")
STATUS_TRAVADA = ("aberta", "feita", "descartada")


def _in(vals):
    return "(" + ",".join(f"'{v}'" for v in vals) + ")"


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS candidaturas (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  empresa TEXT NOT NULL,
  titulo TEXT NOT NULL DEFAULT '',
  fonte TEXT,
  url TEXT,
  url_norm TEXT,
  chave TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN {_in(STATUS_CAND)}),
  fit INTEGER,
  obs TEXT,
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  atualizado_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_cand_url ON candidaturas(url_norm);
CREATE INDEX IF NOT EXISTS ix_cand_chave ON candidaturas(chave);
CREATE INDEX IF NOT EXISTS ix_cand_data ON candidaturas(data);

CREATE TABLE IF NOT EXISTS descartes (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  empresa TEXT NOT NULL,
  titulo TEXT NOT NULL DEFAULT '',
  fonte TEXT,
  url TEXT,
  url_norm TEXT,
  chave TEXT NOT NULL,
  motivo TEXT,
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_desc_url ON descartes(url_norm);
CREATE INDEX IF NOT EXISTS ix_desc_chave ON descartes(chave);

CREATE TABLE IF NOT EXISTS vistas_legado (
  url_norm TEXT PRIMARY KEY,
  contexto TEXT
);

CREATE TABLE IF NOT EXISTS perguntas (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  pergunta TEXT NOT NULL,
  pergunta_norm TEXT NOT NULL,
  tipo_campo TEXT,
  empresa_vaga TEXT,
  plataforma TEXT,
  url TEXT,
  resposta_agente TEXT,
  resposta_oficial TEXT,
  status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN {_in(STATUS_PERG)}),
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_perg_norm ON perguntas(pergunta_norm);

CREATE TABLE IF NOT EXISTS sites_bloqueados (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  site TEXT NOT NULL,
  url TEXT,
  tentando TEXT,
  motivo TEXT NOT NULL CHECK (motivo IN {_in(MOTIVOS_SITE)}),
  detalhe TEXT,
  tentativas INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'bloqueado' CHECK (status IN {_in(STATUS_SITE)}),
  resolucao TEXT,
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS contatos (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  pessoa TEXT NOT NULL,
  pessoa_norm TEXT NOT NULL,
  empresa TEXT,
  canal TEXT NOT NULL CHECK (canal IN {_in(CANAIS)}),
  direcao TEXT NOT NULL CHECK (direcao IN ('enviado','recebido')),
  resumo TEXT,
  candidatura_id INTEGER REFERENCES candidaturas(id),
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_cont_pessoa ON contatos(pessoa_norm);

CREATE TABLE IF NOT EXISTS pendencias (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  descricao TEXT NOT NULL,
  prazo TEXT,
  url TEXT,
  candidatura_id INTEGER REFERENCES candidaturas(id),
  status TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta','feita','descartada')),
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  resolvido_em TEXT
);

CREATE TABLE IF NOT EXISTS travadas (
  id INTEGER PRIMARY KEY,
  data TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN {_in(TIPOS_TRAVADA)}),
  empresa TEXT,
  titulo TEXT,
  chave TEXT,
  url TEXT,
  url_norm TEXT NOT NULL DEFAULT '',
  url_form TEXT,
  site TEXT,
  rotina TEXT,
  fit INTEGER,
  etapa TEXT,
  campos TEXT,
  detalhe TEXT,
  obs TEXT,
  candidatura_id INTEGER REFERENCES candidaturas(id),
  status TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN {_in(STATUS_TRAVADA)}),
  resolucao TEXT,
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  resolvido_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_trav_url ON travadas(url_norm);
CREATE INDEX IF NOT EXISTS ix_trav_chave ON travadas(chave);

CREATE TABLE IF NOT EXISTS controle (
  chave TEXT PRIMARY KEY,
  valor TEXT,
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS sessao_log (
  id INTEGER PRIMARY KEY,
  data_rodada TEXT NOT NULL,
  ts TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  tipo TEXT NOT NULL,
  texto TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_log_data ON sessao_log(data_rodada);

CREATE TABLE IF NOT EXISTS historico (
  id INTEGER PRIMARY KEY,
  origem TEXT NOT NULL,
  secao TEXT,
  texto TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  ordem INTEGER NOT NULL DEFAULT 100,
  tema TEXT NOT NULL,
  gancho TEXT,
  texto TEXT NOT NULL,
  imagem TEXT,
  status TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho','aprovado','publicado','descartado')),
  publicado_em TEXT,
  url TEXT,
  obs TEXT,
  criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  atualizado_em TEXT
);
"""
TABELAS = ("candidaturas", "descartes", "vistas_legado", "perguntas", "sites_bloqueados",
           "contatos", "pendencias", "travadas", "controle", "sessao_log", "historico", "posts")


# ---------- caps / config ----------
def _caps():
    return config.load_config().get("caps", {})


def _empregador_atual():
    """Formas normalizadas (só letras/números) do empregador atual (nunca sinalizar interesse nele)."""
    return [re.sub(r"[^a-z0-9]", "", slug(e)) for e in config.load_config().get("current_employer", []) if e]


# ---------- normalização ----------
def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s).lower()).strip("-")


SENIORIDADE = re.compile(r"\b(senior|sr|pleno|ssr)\b\.?")


# Local/modalidade/contrato no título não muda a vaga — repostagens costumam só trocar isso.
RUIDO_TITULO = re.compile(
    r"\b(remote|remoto|remota|work from home|wfh|work|latam|latin america|americas|south america|brazil|brasil|"
    r"worldwide|global|anywhere|usa|us|canada|europe|emea|contract|contractor|freelance|pj|clt|full[ -]?time|"
    r"part[ -]?time|hybrid|hibrido|presencial|on[ -]?site|100)\b")
RUIDO_EMPRESA = re.compile(r"\b(inc|llc|ltd|ltda|s\.?a|corp|gmbh)\b\.?")


def _titulo_norm(titulo):
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", sem_acento(titulo or "").lower())
    t = SENIORIDADE.sub(" ", t)
    return slug(RUIDO_TITULO.sub(" ", t))


def chave(empresa, titulo):
    emp = RUIDO_EMPRESA.sub(" ", re.sub(r"\(.*?\)", "", sem_acento(empresa or "").lower()))
    return f"{slug(emp)}|{_titulo_norm(titulo)}"


def _parecidos(t1, t2):
    a, b = set(t1.split("-")) - {""}, set(t2.split("-")) - {""}
    return bool(a and b) and len(a & b) / len(a | b) >= 0.75


def norm_url(u):
    if not u:
        return ""
    u = u.strip()
    m = re.search(r"currentJobId=(\d+)", u)
    if m and "linkedin." in u:
        return f"linkedin.com/jobs/view/{m.group(1)}"
    u = u.lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    base, _, query = u.split("#", 1)[0].partition("?")
    ids = sorted(p for p in query.split("&") if p.split("=", 1)[0] in PARAMS_ID)
    return base.rstrip("/") + ("?" + "&".join(ids) if ids else "")


# Parâmetros de query que identificam a vaga (o resto — utm, ref, source — é ruído).
PARAMS_ID = {"positionid", "gh_jid", "jobid", "job_id", "jk", "vjk", "id", "jid", "postingid", "requisitionid"}


def erro(msg, code=1):
    print(f"ERRO {msg}")
    sys.exit(code)


def hoje():
    return datetime.date.today().isoformat()


def agora():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- conexão ----------
def conectar(criar=False, somente_leitura=False):
    if not os.path.exists(DB) and not criar:
        print(f"ERRO:db-ausente {DB} — não crie um banco vazio; rode `jobdb.py init` ou restaure de {BACKUPS}")
        sys.exit(1)
    if somente_leitura:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    else:
        con = sqlite3.connect(DB, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def imprimir(rows, cols=None):
    rows = list(rows)
    if not rows:
        print("(nenhum)")
        return
    cols = cols or rows[0].keys()
    print("\t".join(cols))
    for r in rows:
        print("\t".join("" if r[c] is None else str(r[c]).replace("\n", " / ") for c in cols))


# ---------- dedup ----------
def urls_vistas(con):
    q = """SELECT url_norm FROM candidaturas WHERE url_norm <> ''
           UNION SELECT url_norm FROM descartes WHERE url_norm <> ''
           UNION SELECT url_norm FROM travadas WHERE url_norm <> ''
           UNION SELECT url_norm FROM vistas_legado"""
    return {r[0] for r in con.execute(q)}


def dedup(con, url, empresa, titulo):
    un = norm_url(url)
    if un:
        r = con.execute("SELECT id,status,data FROM candidaturas WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"DUPLICADA candidatura id={r['id']} status={r['status']} data={r['data']} (mesma URL)"
        r = con.execute("SELECT id,data,motivo FROM descartes WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"DESCARTADA-ANTES id={r['id']} data={r['data']} motivo={(r['motivo'] or '')[:120]}"
        r = con.execute("SELECT id,data,tipo,status FROM travadas WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"TRAVADA id={r['id']} tipo={r['tipo']} status={r['status']} data={r['data']} (já está na sua lista — pular)"
        r = con.execute("SELECT contexto FROM vistas_legado WHERE url_norm=?", (un,)).fetchone()
        if r:
            return f"VISTA-LEGADO (URL citada em import antigo: {(r['contexto'] or '')[:120]})"
    if empresa:
        k = chave(empresa, titulo)
        r = con.execute("SELECT id,status,data FROM candidaturas WHERE chave=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"DUPLICADA candidatura id={r['id']} status={r['status']} data={r['data']} (mesma empresa+cargo)"
        r = con.execute("SELECT id,data,motivo FROM descartes WHERE chave=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"DESCARTADA-ANTES id={r['id']} data={r['data']} motivo={(r['motivo'] or '')[:120]}"
        r = con.execute("SELECT id,data,tipo,status FROM travadas WHERE chave=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"TRAVADA id={r['id']} tipo={r['tipo']} status={r['status']} data={r['data']} (mesma empresa+cargo; já está na sua lista — pular)"
        emp, _, tit = k.partition("|")
        for r in con.execute("SELECT id,status,data,titulo,chave FROM candidaturas WHERE chave LIKE ?", (emp + "|%",)):
            if _parecidos(tit, r["chave"].partition("|")[2]):
                return f"DUPLICADA candidatura id={r['id']} status={r['status']} data={r['data']} (mesma empresa, título equivalente: \"{r['titulo']}\")"
    return "NOVA"


# ---------- comandos ----------
def cmd_init(a):
    con = conectar(criar=True)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO controle (chave,valor) VALUES ('schema_version',?) "
                "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor", (SCHEMA_VERSION,))
    con.commit()
    print(f"OK schema em {DB} (schema_version={SCHEMA_VERSION})")


def cmd_check(a):
    if not os.path.exists(DB):
        print(f"ERRO:db-ausente {DB}")
        sys.exit(1)
    try:
        con = conectar()
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            print(f"ERRO:integridade {ok}")
            sys.exit(1)
        existentes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        faltando = [t for t in TABELAS if t not in existentes]
        if faltando:
            print(f"ERRO:tabelas-faltando {','.join(faltando)}")
            sys.exit(1)
        for t in TABELAS:
            print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
        r = con.execute("SELECT valor FROM controle WHERE chave='schema_version'").fetchone()
        ver = r[0] if r else None
        if ver and ver != SCHEMA_VERSION:
            print(f"AVISO:schema-version banco={ver} motor={SCHEMA_VERSION} (drift entre cópias do engine — ressincronize)")
    except sqlite3.Error as e:
        print(f"ERRO:sqlite {e}")
        sys.exit(1)
    print("OK")


def cmd_backup(a):
    con = conectar()
    os.makedirs(BACKUPS, exist_ok=True)
    destino = os.path.join(BACKUPS, f"state-{datetime.datetime.now():%Y-%m-%d_%H%M}.db")
    with sqlite3.connect(destino) as dst:
        con.backup(dst)
    antigos = sorted(f for f in os.listdir(BACKUPS) if f.startswith("state-") and f.endswith(".db"))
    for f in antigos[:-KEEP_BACKUPS]:
        os.remove(os.path.join(BACKUPS, f))
    print(f"OK {destino}")


def cmd_dedup(a):
    print(dedup(conectar(somente_leitura=True), a.url, a.empresa, a.titulo))


def cmd_add_candidatura(a):
    if a.status not in STATUS_CAND:
        erro(f"status inválido: {a.status} (válidos: {', '.join(STATUS_CAND)})")
    con = conectar()
    d = dedup(con, a.url, a.empresa, a.titulo)
    if d != "NOVA":
        print(d)
        if d.startswith("DESCARTADA-ANTES"):
            print("NAO-GRAVADO — vaga já descartada no gate; --force não vale aqui (só você reverte um descarte)")
            sys.exit(2)
        if not a.force:
            print("NAO-GRAVADO (use --force --motivo-force \"..\" só se for vaga genuinamente diferente)")
            sys.exit(2)
        if not a.motivo_force:
            erro("--force exige --motivo-force explicando por que é outra vaga", 2)
    _barra_segredo(a.obs)
    cur = con.execute(
        "INSERT INTO candidaturas (data,empresa,titulo,fonte,url,url_norm,chave,status,fit,obs) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (a.data or hoje(), a.empresa, a.titulo or "", a.fonte, a.url, norm_url(a.url),
         chave(a.empresa, a.titulo), a.status, a.fit, a.obs))
    if a.force and d != "NOVA":
        con.execute("INSERT INTO pendencias (data,descricao,url,candidatura_id) VALUES (?,?,?,?)",
                    (hoje(), f"Revisar candidatura FORÇADA id={cur.lastrowid} ({a.empresa} — {a.titulo}): {a.motivo_force} | dedup dizia: {d[:150]}",
                     a.url, cur.lastrowid))
    con.commit()
    print(f"OK candidatura id={cur.lastrowid}")


def cmd_update_candidatura(a):
    con = conectar()
    if a.id:
        r = con.execute("SELECT * FROM candidaturas WHERE id=?", (a.id,)).fetchone()
    elif a.url:
        r = con.execute("SELECT * FROM candidaturas WHERE url_norm=? ORDER BY id DESC LIMIT 1", (norm_url(a.url),)).fetchone()
    else:
        erro("informe --id ou --url")
    if not r:
        erro("candidatura não encontrada")
    status = a.status or r["status"]
    if status not in STATUS_CAND:
        erro(f"status inválido: {status}")
    _barra_segredo(a.obs_append)
    obs = r["obs"] or ""
    if a.obs_append:
        obs = (obs + "\n" if obs else "") + f"[{hoje()}] {a.obs_append}"
    fit = a.fit if a.fit is not None else r["fit"]
    con.execute("UPDATE candidaturas SET status=?, obs=?, fit=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                (status, obs, fit, r["id"]))
    con.commit()
    print(f"OK candidatura id={r['id']} status={status}")


def cmd_add_descarte(a):
    con = conectar()
    cur = con.execute(
        "INSERT INTO descartes (data,empresa,titulo,fonte,url,url_norm,chave,motivo) VALUES (?,?,?,?,?,?,?,?)",
        (a.data or hoje(), a.empresa, a.titulo or "", a.fonte, a.url, norm_url(a.url), chave(a.empresa, a.titulo), a.motivo))
    con.commit()
    print(f"OK descarte id={cur.lastrowid}")


def cmd_candidaturas(a):
    con = conectar(somente_leitura=True)
    where, args = [], []
    if a.data:
        where.append("data=?"); args.append(a.data)
    if a.status:
        where.append("status=?"); args.append(a.status)
    if a.busca:
        where.append("(empresa LIKE ? OR titulo LIKE ? OR obs LIKE ?)"); args += [f"%{a.busca}%"] * 3
    sql = "SELECT id,data,empresa,titulo,fonte,status,fit,url FROM candidaturas"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY data DESC, id DESC LIMIT {int(a.limite)}"
    imprimir(con.execute(sql, args))


def cmd_hoje(a):
    con = conectar(somente_leitura=True)
    d = a.data or hoje()
    n = con.execute("SELECT COUNT(*) FROM candidaturas WHERE data=? AND status<>'incerta'", (d,)).fetchone()[0]
    print(f"CANDIDATURAS_CONTAM={n}")
    imprimir(con.execute("SELECT id,empresa,titulo,status,url FROM candidaturas WHERE data=? ORDER BY id", (d,)))


def cmd_add_pergunta(a):
    _barra_segredo(a.pergunta, a.resposta_agente)
    con = conectar()
    pn = slug(a.pergunta)
    r = con.execute("SELECT id,empresa_vaga FROM perguntas WHERE pergunta_norm=?", (pn,)).fetchone()
    if r:
        if a.empresa_vaga and a.empresa_vaga not in (r["empresa_vaga"] or ""):
            con.execute("UPDATE perguntas SET empresa_vaga=? WHERE id=?",
                        (((r["empresa_vaga"] or "") + "; " + a.empresa_vaga).strip("; "), r["id"]))
            con.commit()
        print(f"EXISTENTE pergunta id={r['id']} (ocorrência somada)")
        return
    cur = con.execute(
        "INSERT INTO perguntas (data,pergunta,pergunta_norm,tipo_campo,empresa_vaga,plataforma,url,resposta_agente) VALUES (?,?,?,?,?,?,?,?)",
        (a.data or hoje(), a.pergunta, pn, a.tipo_campo, a.empresa_vaga, a.plataforma, a.url, a.resposta_agente))
    con.commit()
    print(f"OK pergunta id={cur.lastrowid}")


def cmd_perguntas(a):
    con = conectar(somente_leitura=True)
    sql = "SELECT id,data,status,pergunta,resposta_agente,resposta_oficial FROM perguntas"
    if a.com_resposta:
        sql += " WHERE resposta_oficial IS NOT NULL AND resposta_oficial<>''"
    elif a.status:
        sql += f" WHERE status='{a.status}'" if a.status in STATUS_PERG else ""
    imprimir(con.execute(sql + " ORDER BY id"))


def cmd_responder_pergunta(a):
    con = conectar()
    n = con.execute("UPDATE perguntas SET resposta_oficial=?, status='respondida' WHERE id=?", (a.resposta, a.id)).rowcount
    con.commit()
    if not n:
        erro(f"pergunta id={a.id} não existe")
    print(f"OK pergunta id={a.id} respondida")


def cmd_add_site(a):
    if a.motivo not in MOTIVOS_SITE:
        erro(f"motivo inválido: {a.motivo} (válidos: {', '.join(MOTIVOS_SITE)})")
    con = conectar()
    r = con.execute("SELECT id,tentativas FROM sites_bloqueados WHERE lower(site)=lower(?) AND status='bloqueado' ORDER BY id DESC LIMIT 1",
                    (a.site,)).fetchone()
    if r:
        con.execute("UPDATE sites_bloqueados SET tentativas=tentativas+1, data=?, motivo=?, detalhe=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                    (a.data or hoje(), a.motivo, a.detalhe, r["id"]))
        con.commit()
        print(f"OK site id={r['id']} tentativas={r['tentativas'] + 1}")
        return
    cur = con.execute("INSERT INTO sites_bloqueados (data,site,url,tentando,motivo,detalhe) VALUES (?,?,?,?,?,?)",
                      (a.data or hoje(), a.site, a.url, a.tentando, a.motivo, a.detalhe))
    con.commit()
    print(f"OK site id={cur.lastrowid}")


def cmd_update_site(a):
    if a.status and a.status not in STATUS_SITE:
        erro(f"status inválido: {a.status}")
    con = conectar()
    n = con.execute("UPDATE sites_bloqueados SET status=COALESCE(?,status), resolucao=COALESCE(?,resolucao), atualizado_em=datetime('now','localtime') WHERE id=?",
                    (a.status, a.resolucao, a.id)).rowcount
    con.commit()
    if not n:
        erro(f"site id={a.id} não existe")
    print(f"OK site id={a.id}")


def cooldown(motivo, tentativas, data):
    if motivo not in ("linkedin-bloqueio", "captcha-persistente"):
        return ""
    if tentativas >= 3:
        return "desativada — precisa de você"
    horas = 24 if tentativas <= 1 else 72
    try:
        fim = datetime.datetime.fromisoformat(data) + datetime.timedelta(hours=horas)
        return f"cooldown até {fim:%Y-%m-%d}" if fim > datetime.datetime.now() else "cooldown vencido"
    except ValueError:
        return ""


def cmd_sites_ativos(a):
    con = conectar(somente_leitura=True)
    rows = con.execute("SELECT id,data,site,motivo,tentativas,status FROM sites_bloqueados WHERE status IN ('bloqueado','descartado') ORDER BY site").fetchall()
    if not rows:
        print("(nenhum)")
    for r in rows:
        print(f"{r['id']}\t{r['site']}\t{r['status']}\t{r['motivo']}\ttentativas={r['tentativas']}\t{r['data']}\t{cooldown(r['motivo'], r['tentativas'], r['data'])}")


def cmd_add_contato(a):
    if a.canal not in CANAIS:
        erro(f"canal inválido: {a.canal} (válidos: {', '.join(CANAIS)})")
    _barra_segredo(a.resumo)
    con = conectar()
    cur = con.execute("INSERT INTO contatos (data,pessoa,pessoa_norm,empresa,canal,direcao,resumo,candidatura_id) VALUES (?,?,?,?,?,?,?,?)",
                      (a.data or hoje(), a.pessoa, slug(a.pessoa), a.empresa, a.canal, a.direcao, a.resumo, a.candidatura_id))
    con.commit()
    print(f"OK contato id={cur.lastrowid}")


def cmd_contato_recente(a):
    con = conectar(somente_leitura=True)
    desde = (datetime.date.today() - datetime.timedelta(days=a.dias)).isoformat()
    filtro, args = "", [slug(a.pessoa), desde]
    if a.canal:
        filtro, args = " AND canal=?", args + [a.canal]
    r = con.execute("SELECT data,canal,resumo FROM contatos WHERE pessoa_norm=? AND direcao='enviado' AND data>=?" + filtro +
                    " ORDER BY data DESC LIMIT 1", args).fetchone()
    if r:
        print(f"SIM {r['data']} {r['canal']} — {(r['resumo'] or '')[:120]}")
        return
    # registros antigos (antes da tabela contatos) só existem como texto na obs das candidaturas
    extra = " AND (obs LIKE '%DM%' OR fonte LIKE '%Messag%')" if a.canal == "linkedin-dm" else ""
    r = con.execute("SELECT id,data FROM candidaturas WHERE data>=? AND (empresa LIKE ? OR obs LIKE ?)" + extra +
                    " ORDER BY data DESC LIMIT 1", (desde, f"%{a.pessoa}%", f"%{a.pessoa}%")).fetchone()
    if r:
        print(f"POSSIVEL nome citado na candidatura id={r['id']} de {r['data']} — trate como SIM")
        return
    print("NAO")


def cmd_social_hoje(a):
    con = conectar(somente_leitura=True)
    teto = int(_caps().get("social_per_day", 0))
    n = con.execute("SELECT COUNT(*) FROM contatos WHERE direcao='enviado' AND canal LIKE 'linkedin-%' AND canal<>'linkedin-interesse' AND data=?",
                    (hoje(),)).fetchone()[0]
    print(f"SOCIAL_HOJE={n} TETO={teto} RESTAM={max(0, teto - n)}")


def cmd_interesse_check(a):
    """Pode clicar "I'm interested" na página da empresa? Uma vez a cada N dias por empresa, teto diário, nunca o empregador atual."""
    con = conectar(somente_leitura=True)
    teto = int(_caps().get("interest_per_day", 0))
    cooldown_dias = int(_caps().get("interest_cooldown_days", 180))
    empregador = _empregador_atual()
    emp = slug(a.empresa)
    emp_alnum = re.sub(r"[^a-z0-9]", "", emp)
    if any(e and e in emp_alnum for e in empregador):
        print("NAO empregador-atual")
        return
    n = con.execute("SELECT COUNT(*) FROM contatos WHERE direcao='enviado' AND canal='linkedin-interesse' AND data=?",
                    (hoje(),)).fetchone()[0]
    if n >= teto:
        print(f"NAO teto-diario ({n}/{teto})")
        return
    desde = (datetime.date.today() - datetime.timedelta(days=cooldown_dias)).isoformat()
    r = con.execute("SELECT data FROM contatos WHERE canal='linkedin-interesse' AND direcao='enviado' AND pessoa_norm=? AND data>=? ORDER BY data DESC LIMIT 1",
                    (emp, desde)).fetchone()
    if r:
        print(f"NAO ja-sinalizado {r['data']}")
        return
    print(f"SIM (hoje {n}/{teto})")


def _ler_texto(a):
    if a.arquivo:
        with open(a.arquivo, encoding="utf-8") as f:
            return f.read().strip()
    return (a.texto or "").strip()


def cmd_add_post(a):
    texto = _ler_texto(a)
    if not texto:
        erro("texto vazio (use --arquivo ou --texto)")
    if a.imagem and not os.path.exists(a.imagem):
        erro(f"imagem não existe: {a.imagem}")
    con = conectar()
    cur = con.execute("INSERT INTO posts (ordem,tema,gancho,texto,imagem,obs) VALUES (?,?,?,?,?,?)",
                      (a.ordem, a.tema, a.gancho, texto, a.imagem, a.obs))
    con.commit()
    print(f"OK post id={cur.lastrowid} status=rascunho ({len(texto)} caracteres)")


def cmd_posts(a):
    con = conectar(somente_leitura=True)
    q, args = "SELECT id,ordem,status,tema,gancho,length(texto) AS chars,CASE WHEN imagem IS NULL THEN '' ELSE 'sim' END AS img,publicado_em FROM posts", []
    if a.status:
        q, args = q + " WHERE status=?", [a.status]
    imprimir(con.execute(q + " ORDER BY CASE status WHEN 'publicado' THEN 1 ELSE 0 END, ordem, id", args))


def cmd_post_show(a):
    con = conectar(somente_leitura=True)
    r = con.execute("SELECT * FROM posts WHERE id=?", (a.id,)).fetchone()
    if not r:
        erro(f"post {a.id} não existe")
    print(f"# post {r['id']} — {r['status']} — tema: {r['tema']} — gancho: {r['gancho']} — imagem: {r['imagem'] or 'nenhuma'}")
    print(r["texto"])


def cmd_post_status(a):
    con = conectar()
    n = con.execute("UPDATE posts SET status=?, obs=COALESCE(obs||' | ','')||COALESCE(?,''), atualizado_em=datetime('now','localtime') WHERE id=?",
                    (a.status, a.obs, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} → {a.status}" if n else f"ERRO post {a.id} não existe")


def cmd_post_editar(a):
    texto = _ler_texto(a)
    if not texto:
        erro("texto vazio")
    con = conectar()
    n = con.execute("UPDATE posts SET texto=?, status='rascunho', atualizado_em=datetime('now','localtime') WHERE id=? AND status<>'publicado'",
                    (texto, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} atualizado (volta para rascunho — precisa de nova aprovação)" if n else "ERRO post inexistente ou já publicado")


def cmd_post_proximo(a):
    """Rotina: há post para publicar hoje? Só 'aprovado', só se o último publicado foi há >= INTERVALO dias."""
    con = conectar(somente_leitura=True)
    intervalo = int(_caps().get("post_interval_days", 7))
    ult = con.execute("SELECT MAX(publicado_em) FROM posts WHERE status='publicado'").fetchone()[0]
    if ult:
        prox = datetime.date.fromisoformat(ult[:10]) + datetime.timedelta(days=intervalo)
        if datetime.date.today() < prox:
            print(f"AGUARDAR proximo em {prox.isoformat()} (último publicado {ult[:10]})")
            return
    r = con.execute("SELECT * FROM posts WHERE status='aprovado' ORDER BY ordem, id LIMIT 1").fetchone()
    if not r:
        print("FILA_VAZIA (nenhum post aprovado)")
        return
    print(f"PUBLICAR id={r['id']} imagem={r['imagem'] or 'nenhuma'}")
    print("-----")
    print(r["texto"])


def cmd_post_publicado(a):
    con = conectar()
    n = con.execute("UPDATE posts SET status='publicado', publicado_em=?, url=?, atualizado_em=datetime('now','localtime') WHERE id=? AND status='aprovado'",
                    (agora(), a.url, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} publicado" if n else f"ERRO post {a.id} não está 'aprovado'")


def cmd_interesse_pendentes(a):
    """Empresas com candidatura de fit alto (ou em processo) nos últimos N dias que ainda não receberam "I'm interested"."""
    con = conectar(somente_leitura=True)
    cooldown_dias = int(_caps().get("interest_cooldown_days", 180))
    empregador = _empregador_atual()
    desde = (datetime.date.today() - datetime.timedelta(days=a.dias)).isoformat()
    desde_cd = (datetime.date.today() - datetime.timedelta(days=cooldown_dias)).isoformat()
    feitas = {r[0] for r in con.execute("SELECT pessoa_norm FROM contatos WHERE canal='linkedin-interesse' AND direcao='enviado' AND data>=?", (desde_cd,))}
    rows = con.execute("SELECT id,data,empresa,titulo,fit,status FROM candidaturas WHERE data>=? AND status NOT IN ('rejeitada','desistiu','incerta') "
                       "AND (fit>=? OR status IN ('em-processo','entrevista','teste-pendente')) ORDER BY COALESCE(fit,0) DESC, data DESC",
                       (desde, a.min_fit)).fetchall()
    vistos, n = set(), 0
    for r in rows:
        emp = slug(r["empresa"])
        emp_alnum = re.sub(r"[^a-z0-9]", "", emp)
        if emp in feitas or emp in vistos or any(e and e in emp_alnum for e in empregador):
            continue
        vistos.add(emp)
        print(f"{r['empresa']}	candidatura={r['id']}	fit={r['fit']}	{r['status']}	{r['data']}	{r['titulo']}")
        n += 1
        if n >= a.limite:
            break
    if not n:
        print("(nenhuma)")


def cmd_linkedin_status(a):
    con = conectar(somente_leitura=True)
    r = con.execute("SELECT data,detalhe FROM sites_bloqueados WHERE motivo='linkedin-bloqueio' AND status='bloqueado' ORDER BY data DESC LIMIT 1").fetchone()
    print(f"BLOQUEADO desde {r['data']} — só volta quando você marcar resolvido ({(r['detalhe'] or '')[:100]})" if r else "OK")


LOCK = "NAVEGADOR_LOCK"


def cmd_lock(a):
    if a.acao == "esperar":
        # Espera DENTRO da chamada (a rotina não pode encerrar o turno para esperar: execução agendada não volta sozinha).
        import subprocess, time
        fim = time.time() + a.minutos * 60
        while True:
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "lock", "adquirir", "--dono", a.dono,
                                "--ttl-min", str(a.ttl_min)], capture_output=True, text=True, encoding="utf-8")
            if r.returncode == 0:
                print(r.stdout.strip())
                return
            if time.time() + 30 > fim:
                print(r.stdout.strip() + f" — ainda ocupado após {a.minutos} min")
                sys.exit(3)
            time.sleep(30)
    con = conectar()
    con.execute("BEGIN IMMEDIATE")
    r = con.execute("SELECT valor FROM controle WHERE chave=?", (LOCK,)).fetchone()
    agora_dt = datetime.datetime.now()
    dono_atual, desde = None, None
    if r and r[0]:
        dono_atual, _, ts = r[0].partition("|")
        desde = datetime.datetime.fromisoformat(ts)
    if a.acao == "check":
        con.rollback()
        if dono_atual == a.dono:
            print(f"OK lock ativo de {a.dono}")
            return
        print(f"PARE: a trava não é mais de {a.dono} (atual: {dono_atual or 'ninguém'}) — a execução que te disparou acabou")
        sys.exit(4)
    if a.acao == "adquirir":
        expirado = desde is None or agora_dt - desde > datetime.timedelta(minutes=a.ttl_min)
        if dono_atual and dono_atual != a.dono and not expirado:
            con.rollback()
            print(f"OCUPADO por {dono_atual} desde {desde:%H:%M}")
            sys.exit(3)
        con.execute("INSERT INTO controle (chave,valor) VALUES (?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=datetime('now','localtime')",
                    (LOCK, f"{a.dono}|{agora_dt:%Y-%m-%dT%H:%M:%S}"))
        con.commit()
        print(f"OK lock={a.dono}" + (f" (tomado de {dono_atual}, expirado)" if dono_atual and dono_atual != a.dono else ""))
    else:
        if dono_atual == a.dono:
            con.execute("DELETE FROM controle WHERE chave=?", (LOCK,))
        con.commit()
        print("OK liberado" if dono_atual == a.dono else f"OK (lock era de {dono_atual or 'ninguém'}, nada feito)")


def cmd_controle(a):
    if a.acao == "show":
        imprimir(conectar(somente_leitura=True).execute("SELECT chave,valor,atualizado_em FROM controle ORDER BY chave"))
    elif a.acao == "get":
        r = conectar(somente_leitura=True).execute("SELECT valor FROM controle WHERE chave=?", (a.pares[0],)).fetchone()
        print(r[0] if r else "")
    elif a.acao == "set":
        con = conectar()
        for p in a.pares:
            if "=" not in p:
                erro(f"use CHAVE=valor (recebi {p})")
            k, v = p.split("=", 1)
            if v == "":
                con.execute("DELETE FROM controle WHERE chave=?", (k.strip(),))
            else:
                con.execute("INSERT INTO controle (chave,valor) VALUES (?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=datetime('now','localtime')",
                            (k.strip(), v))
        con.commit()
        print("OK")


def cmd_log(a):
    _barra_segredo(a.texto)
    con = conectar()
    con.execute("INSERT INTO sessao_log (data_rodada,tipo,texto) VALUES (?,?,?)", (a.data_rodada or hoje(), a.tipo, a.texto))
    con.commit()
    print("OK")


def cmd_logs(a):
    imprimir(conectar(somente_leitura=True).execute(
        "SELECT ts,tipo,texto FROM sessao_log WHERE data_rodada=? ORDER BY id", (a.data or hoje(),)))


def cmd_pendencia(a):
    con = conectar()
    if a.acao == "add":
        _barra_segredo(a.descricao)
        abertas = con.execute("SELECT id,descricao,url FROM pendencias WHERE status='aberta'").fetchall()
        un = norm_url(a.url)
        for p in abertas:
            if (un and norm_url(p["url"]) == un) or _parecidos(slug(p["descricao"])[:120], slug(a.descricao)[:120]):
                print(f"EXISTENTE pendencia id={p['id']} (já aberta: {p['descricao'][:100]})")
                return
        cur = con.execute("INSERT INTO pendencias (data,descricao,prazo,url,candidatura_id) VALUES (?,?,?,?,?)",
                          (hoje(), a.descricao, a.prazo, a.url, a.candidatura_id))
        con.commit()
        print(f"OK pendencia id={cur.lastrowid}")
    elif a.acao in ("feita", "descartada"):
        con.execute("UPDATE pendencias SET status=?, resolvido_em=datetime('now','localtime') WHERE id=?", (a.acao, a.id))
        con.commit()
        print(f"OK pendencia id={a.id} {a.acao}")
    else:
        imprimir(con.execute("SELECT id,data,prazo,descricao,url FROM pendencias WHERE status='aberta' ORDER BY COALESCE(prazo,'9999'), id"))


# Guarda anti-segredo: nunca gravar no banco o VALOR de documento, cartão ou senha — só a
# descrição do campo. Rede de segurança (defesa em profundidade); o agente já é instruído a nunca
# gravar segredos. Aplicada a todo campo de texto livre no ponto de escrita.
PARECE_DOC = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")          # CPF
PARECE_CARTAO = re.compile(r"\b(?:\d[ -]?){13,19}\b")                 # cartão / sequência longa de dígitos
PARECE_SENHA = re.compile(r"\b(senha|password|passwd|pwd|secret|token)\b\s*[:=]\s*\S+", re.I)


def _segredo_em(*campos):
    """Devolve o motivo se algum campo parece conter um segredo, senão None."""
    for c in campos:
        if not c:
            continue
        if PARECE_DOC.search(c):
            return "número de documento (ex.: CPF)"
        if PARECE_CARTAO.search(c):
            return "sequência longa de dígitos (cartão/documento)"
        if PARECE_SENHA.search(c):
            return "senha/token em texto plano"
    return None


def _barra_segredo(*campos):
    m = _segredo_em(*campos)
    if m:
        erro(f"texto parece conter {m} — descreva o campo (ex.: \"CPF obrigatório\"), nunca grave o valor")


def cmd_travada(a):
    con = conectar()
    if a.acao == "add":
        if a.tipo not in TIPOS_TRAVADA:
            erro(f"tipo inválido: {a.tipo} (válidos: {', '.join(TIPOS_TRAVADA)})")
        _barra_segredo(a.campos, a.detalhe, a.obs, a.etapa)
        un = norm_url(a.url)
        k = chave(a.empresa, a.titulo) if a.empresa else None
        r = None
        if un:
            r = con.execute("SELECT id,tipo FROM travadas WHERE url_norm=? AND status='aberta' LIMIT 1", (un,)).fetchone()
        if not r and k:
            r = con.execute("SELECT id,tipo FROM travadas WHERE chave=? AND status='aberta' LIMIT 1", (k,)).fetchone()
        if r:
            print(f"EXISTENTE travada id={r['id']} tipo={r['tipo']} (já aberta)")
            return
        cur = con.execute(
            "INSERT INTO travadas (data,tipo,empresa,titulo,chave,url,url_norm,url_form,site,rotina,fit,etapa,campos,detalhe,obs,candidatura_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (a.data or hoje(), a.tipo, a.empresa, a.titulo, k, a.url, un, a.url_form, a.site, a.rotina, a.fit,
             a.etapa, a.campos, a.detalhe, a.obs, a.candidatura_id))
        con.commit()
        print(f"OK travada id={cur.lastrowid}")
    elif a.acao in ("feita", "descartada"):
        if not a.id:
            erro(f"travada {a.acao} exige --id")
        con.execute("UPDATE travadas SET status=?, resolucao=COALESCE(?,resolucao), resolvido_em=datetime('now','localtime') WHERE id=?",
                    (a.acao, a.resolucao, a.id))
        con.commit()
        print(f"OK travada id={a.id} {a.acao}")
    else:
        cond, params = ["status=?"], [a.status or "aberta"]
        if a.tipo:
            cond.append("tipo=?"); params.append(a.tipo)
        if a.rotina:
            cond.append("rotina=?"); params.append(a.rotina)
        imprimir(con.execute(
            f"SELECT id,data,tipo,empresa,titulo,fit,etapa,campos,url,url_form,site,rotina,detalhe FROM travadas WHERE {' AND '.join(cond)}"
            " ORDER BY COALESCE(fit,0) DESC, id", params))


def cmd_relatorio(a):
    con = conectar(somente_leitura=True)
    d = a.data or hoje()
    cands = con.execute("SELECT empresa,titulo,status,url,fonte FROM candidaturas WHERE data=? ORDER BY id", (d,)).fetchall()
    validas = [c for c in cands if c["status"] != "incerta"]
    incertas = [c for c in cands if c["status"] == "incerta"]
    print(f"# Resumo {d} — {len(validas)} candidaturas\n")
    print(f"## Candidaturas ({len(validas)})")
    for c in validas:
        print(f"- {c['empresa']} — {c['titulo']} — {c['status']} — {c['fonte'] or ''} — {c['url'] or 'sem URL'}")
    if incertas:
        print(f"\n## Incertas — enviadas sem confirmação, não contam ({len(incertas)})")
        for c in incertas:
            print(f"- {c['empresa']} — {c['titulo']} — {c['url'] or 'sem URL'}")
    logs = con.execute("SELECT ts,tipo,texto FROM sessao_log WHERE data_rodada=? ORDER BY id", (d,)).fetchall()
    if logs:
        print("\n## Log da rodada")
        for l in logs:
            print(f"- {l['ts'][11:16]} [{l['tipo']}] {l['texto']}")
    novos_sites = con.execute("SELECT site,motivo,detalhe FROM sites_bloqueados WHERE data=?", (d,)).fetchall()
    if novos_sites:
        print("\n## Sites bloqueados hoje")
        for s in novos_sites:
            print(f"- {s['site']} — {s['motivo']} — {(s['detalhe'] or '')[:160]}")
    novas_perg = con.execute("SELECT pergunta,resposta_agente FROM perguntas WHERE data=?", (d,)).fetchall()
    if novas_perg:
        print("\n## Perguntas novas (responder)")
        for p in novas_perg:
            print(f"- {p['pergunta'][:200]} → agente respondeu: {(p['resposta_agente'] or '')[:120]}")
    trav = con.execute("SELECT id,data,tipo,empresa,titulo,fit,etapa,campos,url,url_form FROM travadas WHERE status='aberta'"
                       " ORDER BY tipo, COALESCE(fit,0) DESC, id").fetchall()
    if trav:
        print(f"\n## Vagas travadas — você termina na mão ({len(trav)} abertas)")
        tipo_atual = None
        for t in trav:
            if t["tipo"] != tipo_atual:
                tipo_atual = t["tipo"]
                print(f"\n**{tipo_atual}**")
            fit = f" (fit {t['fit']})" if t["fit"] else ""
            onde = f" — parou em: {t['etapa']}" if t["etapa"] else ""
            faltam = f" — falta: {t['campos']}" if t["campos"] else ""
            link = t["url_form"] or t["url"] or "sem URL"
            print(f"- #{t['id']} {t['empresa'] or '?'} — {t['titulo'] or '?'}{fit}{onde}{faltam} — {link}")
    pend = con.execute("SELECT id,prazo,descricao,url FROM pendencias WHERE status='aberta' ORDER BY COALESCE(prazo,'9999'), id").fetchall()
    print(f"\n## Precisa de você ({len(pend)} abertas)")
    for p in pend:
        prazo = f"[prazo {p['prazo']}] " if p["prazo"] else ""
        print(f"- #{p['id']} {prazo}{p['descricao']}" + (f" — {p['url']}" if p["url"] else ""))


RESPONDEU = ("em-processo", "entrevista", "oferta", "teste-pendente", "rejeitada")
ENTREVISTOU = ("entrevista", "oferta")


def cmd_metricas(a):
    """Funil e taxa de resposta por fonte — só agrega o que já está no banco."""
    con = conectar(somente_leitura=True)
    rows = con.execute("SELECT fonte,status FROM candidaturas WHERE status<>'incerta'").fetchall()
    total = len(rows)
    agg = {}
    for r in rows:
        fonte = (r["fonte"] or "(sem fonte)").split(" ")[0]
        d = agg.setdefault(fonte, {"n": 0, "resp": 0, "entr": 0})
        d["n"] += 1
        if r["status"] in RESPONDEU:
            d["resp"] += 1
        if r["status"] in ENTREVISTOU:
            d["entr"] += 1
    resp_tot = sum(1 for r in rows if r["status"] in RESPONDEU)
    entr_tot = sum(1 for r in rows if r["status"] in ENTREVISTOU)
    pct = lambda x, n: f"{(100 * x / n):.0f}%" if n else "—"
    print(f"# Métricas — {total} candidaturas (exclui incertas)")
    print(f"Taxa de resposta: {pct(resp_tot, total)} ({resp_tot}) | Taxa de entrevista: {pct(entr_tot, total)} ({entr_tot})\n")
    print("fonte\tcandidaturas\trespostas\ttaxa_resp\tentrevistas\ttaxa_entr")
    for fonte, d in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
        print(f"{fonte}\t{d['n']}\t{d['resp']}\t{pct(d['resp'], d['n'])}\t{d['entr']}\t{pct(d['entr'], d['n'])}")


def cmd_followups(a):
    """Candidaturas aplicadas/sem-retorno há >= N dias (default 7) — para follow-up (o agente/você decide)."""
    con = conectar(somente_leitura=True)
    limite = (datetime.date.today() - datetime.timedelta(days=a.dias)).isoformat()
    rows = con.execute(
        "SELECT id,data,empresa,titulo,fonte,status,url FROM candidaturas "
        "WHERE status IN ('aplicada','sem-retorno') AND data<=? ORDER BY data, id", (limite,)).fetchall()
    if not rows:
        print("(nenhuma)")
        return
    imprimir(rows)


def cmd_sql(a):
    con = conectar(somente_leitura=True)
    try:
        imprimir(con.execute(a.consulta))
    except sqlite3.Error as e:
        erro(f"{e}")


def cmd_export(a):
    con = conectar(somente_leitura=True)
    pasta = config.VISAO
    os.makedirs(pasta, exist_ok=True)
    if getattr(a, "csv", False):
        import csv
        destino = os.path.join(pasta, "candidaturas.csv")
        rows = con.execute("SELECT id,data,empresa,titulo,fonte,status,fit,url,obs FROM candidaturas ORDER BY data DESC, id DESC").fetchall()
        with open(destino, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "data", "empresa", "titulo", "fonte", "status", "fit", "url", "obs"])
            for r in rows:
                w.writerow([r[c] for c in ("id", "data", "empresa", "titulo", "fonte", "status", "fit", "url", "obs")])
        print(f"OK {destino}")
        return
    vistas = {
        "candidaturas.md": "SELECT data,empresa,titulo,fonte,status,fit,url,obs FROM candidaturas ORDER BY data DESC, id DESC",
        "pendencias.md": "SELECT id,data,prazo,descricao,url FROM pendencias WHERE status='aberta' ORDER BY COALESCE(prazo,'9999')",
        "travadas.md": "SELECT id,data,tipo,empresa,titulo,fit,etapa,campos,url,url_form,site,rotina,detalhe FROM travadas WHERE status='aberta' ORDER BY tipo, COALESCE(fit,0) DESC",
        "perguntas.md": "SELECT id,status,pergunta,resposta_agente,resposta_oficial FROM perguntas ORDER BY status, id",
        "sites-bloqueados.md": "SELECT id,data,site,motivo,tentativas,status,detalhe FROM sites_bloqueados ORDER BY status, site",
    }
    for nome, sql in vistas.items():
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.execute(sql).description]
        with open(os.path.join(pasta, nome), "w", encoding="utf-8") as f:
            f.write(f"> Gerado por `jobdb.py export` em {agora()} — só leitura; editar pelo jobdb.py.\n\n")
            f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
            for r in rows:
                f.write("| " + " | ".join("" if r[c] is None else str(r[c]).replace("|", "/").replace("\n", " ") for c in cols) + " |\n")
    print(f"OK {pasta}")


# ---------- CLI ----------
def main():
    p = argparse.ArgumentParser(description="Aplica — banco do motor de candidatura (SQLite)")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init", help="cria as tabelas (idempotente)").set_defaults(f=cmd_init)
    sp.add_parser("check", help="health-check: arquivo, integridade e tabelas. Última linha OK ou ERRO:<motivo>").set_defaults(f=cmd_check)
    sp.add_parser("backup", help=f"cópia consistente em backups/ (mantém {KEEP_BACKUPS})").set_defaults(f=cmd_backup)

    s = sp.add_parser("dedup", help="NOVA | DUPLICADA ... | DESCARTADA-ANTES ... | VISTA-LEGADO ...")
    s.add_argument("--url"); s.add_argument("--empresa"); s.add_argument("--titulo")
    s.set_defaults(f=cmd_dedup)

    s = sp.add_parser("add-candidatura", help="grava candidatura (roda dedup antes; exit 2 se duplicada)")
    s.add_argument("--empresa", required=True); s.add_argument("--titulo", required=True)
    s.add_argument("--fonte"); s.add_argument("--url"); s.add_argument("--data")
    s.add_argument("--status", default="aplicada"); s.add_argument("--fit", type=int); s.add_argument("--obs")
    s.add_argument("--force", action="store_true", help="só para vaga genuinamente diferente marcada DUPLICADA; nunca para DESCARTADA-ANTES")
    s.add_argument("--motivo-force", help="obrigatório com --force; vira pendência para você revisar")
    s.set_defaults(f=cmd_add_candidatura)

    s = sp.add_parser("update-candidatura", help="muda status e/ou anexa nota datada")
    s.add_argument("--id", type=int); s.add_argument("--url"); s.add_argument("--status")
    s.add_argument("--obs-append"); s.add_argument("--fit", type=int)
    s.set_defaults(f=cmd_update_candidatura)

    s = sp.add_parser("add-descarte", help="vaga que passou no dedup mas caiu no gate")
    s.add_argument("--empresa", required=True); s.add_argument("--titulo", default="")
    s.add_argument("--url"); s.add_argument("--fonte"); s.add_argument("--motivo", required=True); s.add_argument("--data")
    s.set_defaults(f=cmd_add_descarte)

    s = sp.add_parser("candidaturas", help="lista/busca candidaturas")
    s.add_argument("--data"); s.add_argument("--status"); s.add_argument("--busca"); s.add_argument("--limite", default=50)
    s.set_defaults(f=cmd_candidaturas)

    s = sp.add_parser("hoje", help="candidaturas do dia (CANDIDATURAS_CONTAM exclui incertas)")
    s.add_argument("--data"); s.set_defaults(f=cmd_hoje)

    s = sp.add_parser("add-pergunta", help="pergunta sem resposta no material (dedup pelo texto)")
    s.add_argument("--pergunta", required=True); s.add_argument("--tipo-campo"); s.add_argument("--empresa-vaga")
    s.add_argument("--plataforma"); s.add_argument("--url"); s.add_argument("--resposta-agente"); s.add_argument("--data")
    s.set_defaults(f=cmd_add_pergunta)

    s = sp.add_parser("perguntas", help="lista perguntas; --com-resposta = as que você já respondeu (valem já)")
    s.add_argument("--status"); s.add_argument("--com-resposta", action="store_true")
    s.set_defaults(f=cmd_perguntas)

    s = sp.add_parser("responder-pergunta", help="grava a resposta oficial")
    s.add_argument("--id", type=int, required=True); s.add_argument("--resposta", required=True)
    s.set_defaults(f=cmd_responder_pergunta)

    s = sp.add_parser("add-site", help="site que travou cadastro/login (soma tentativa se já bloqueado)")
    s.add_argument("--site", required=True); s.add_argument("--motivo", required=True)
    s.add_argument("--url"); s.add_argument("--tentando"); s.add_argument("--detalhe"); s.add_argument("--data")
    s.set_defaults(f=cmd_add_site)

    s = sp.add_parser("update-site", help="marcar resolvido/descartado")
    s.add_argument("--id", type=int, required=True); s.add_argument("--status"); s.add_argument("--resolucao")
    s.set_defaults(f=cmd_update_site)

    sp.add_parser("sites-ativos", help="sites bloqueados/descartados + cooldown").set_defaults(f=cmd_sites_ativos)

    s = sp.add_parser("add-contato", help="contato com recrutador (DM, conexão, comentário, e-mail)")
    s.add_argument("--pessoa", required=True); s.add_argument("--canal", required=True)
    s.add_argument("--direcao", choices=("enviado", "recebido"), required=True)
    s.add_argument("--empresa"); s.add_argument("--resumo"); s.add_argument("--candidatura-id", type=int); s.add_argument("--data")
    s.set_defaults(f=cmd_add_contato)

    s = sp.add_parser("contato-recente", help="regra dos 30 dias: SIM | POSSIVEL | NAO (use --canal linkedin-dm para a regra de DM)")
    s.add_argument("--pessoa", required=True); s.add_argument("--dias", type=int, default=30)
    s.add_argument("--canal", choices=CANAIS, help="só conta contatos deste canal (ex.: linkedin-dm)")
    s.set_defaults(f=cmd_contato_recente)

    x = sp.add_parser("interesse-check", help="pode clicar \"I'm interested\" na página da empresa no LinkedIn? (cooldown por empresa, teto diário, nunca o empregador atual)")
    x.add_argument("--empresa", required=True)
    x.set_defaults(f=cmd_interesse_check)
    x = sp.add_parser("add-post", help="adiciona post à fila (status rascunho — você aprova)")
    x.add_argument("--tema", required=True); x.add_argument("--gancho"); x.add_argument("--arquivo"); x.add_argument("--texto")
    x.add_argument("--imagem"); x.add_argument("--ordem", type=int, default=100); x.add_argument("--obs")
    x.set_defaults(f=cmd_add_post)
    x = sp.add_parser("posts", help="lista a fila de posts"); x.add_argument("--status"); x.set_defaults(f=cmd_posts)
    x = sp.add_parser("post-show", help="mostra o texto de um post"); x.add_argument("--id", type=int, required=True); x.set_defaults(f=cmd_post_show)
    x = sp.add_parser("post-status", help="aprovar/descartar/voltar a rascunho")
    x.add_argument("--id", type=int, required=True); x.add_argument("--status", required=True, choices=["rascunho", "aprovado", "descartado"]); x.add_argument("--obs")
    x.set_defaults(f=cmd_post_status)
    x = sp.add_parser("post-editar", help="troca o texto (volta para rascunho)")
    x.add_argument("--id", type=int, required=True); x.add_argument("--arquivo"); x.add_argument("--texto"); x.set_defaults(f=cmd_post_editar)
    x = sp.add_parser("post-proximo", help="rotina: post aprovado a publicar hoje? (intervalo de caps.post_interval_days)"); x.set_defaults(f=cmd_post_proximo)
    x = sp.add_parser("post-publicado", help="marca post como publicado")
    x.add_argument("--id", type=int, required=True); x.add_argument("--url"); x.set_defaults(f=cmd_post_publicado)
    x = sp.add_parser("interesse-pendentes", help="empresas com candidatura fit alto/em processo ainda sem \"I'm interested\"")
    x.add_argument("--dias", type=int, default=7)
    x.add_argument("--min-fit", type=int, default=90)
    x.add_argument("--limite", type=int, default=3)
    x.set_defaults(f=cmd_interesse_pendentes)
    sp.add_parser("social-hoje", help="ações sociais no LinkedIn enviadas hoje (todas as rotinas) vs teto (caps.social_per_day)").set_defaults(f=cmd_social_hoje)
    sp.add_parser("linkedin-status", help="OK | BLOQUEADO (linkedin-bloqueio ainda não resolvido por você)").set_defaults(f=cmd_linkedin_status)

    s = sp.add_parser("lock", help="trava do navegador: adquirir (exit 3 = OCUPADO) | esperar (bloqueia até --minutos e já adquire; exit 3 = ainda ocupado) | liberar | check (subagente: exit 4 = PARE)")
    s.add_argument("acao", choices=("adquirir", "esperar", "liberar", "check"))
    s.add_argument("--minutos", type=float, default=9, help="esperar: tempo máximo desta chamada (≤9 para caber no limite de 10 min da ferramenta)"); s.add_argument("--dono", required=True)
    s.add_argument("--ttl-min", type=int, default=150, help="lock mais velho que isso é considerado abandonado")
    s.set_defaults(f=cmd_lock)

    s = sp.add_parser("controle", help="bloco CONTROLE DE LOTE: show | get CHAVE | set CHAVE=valor ... (valor vazio apaga)")
    s.add_argument("acao", choices=("show", "get", "set")); s.add_argument("pares", nargs="*")
    s.set_defaults(f=cmd_controle)

    s = sp.add_parser("log", help="linha de auditoria da rodada (lote, monitor, processos, obs)")
    s.add_argument("--tipo", required=True); s.add_argument("--texto", required=True); s.add_argument("--data-rodada")
    s.set_defaults(f=cmd_log)

    s = sp.add_parser("logs", help="log de uma rodada"); s.add_argument("--data"); s.set_defaults(f=cmd_logs)

    s = sp.add_parser("pendencia", help="Precisa de você: list | add | feita | descartada")
    s.add_argument("acao", choices=("list", "add", "feita", "descartada"))
    s.add_argument("--id", type=int); s.add_argument("--descricao"); s.add_argument("--prazo")
    s.add_argument("--url"); s.add_argument("--candidatura-id", type=int)
    s.set_defaults(f=cmd_pendencia)

    s = sp.add_parser("travada", help="item que o agente não conseguiu terminar (documento, senha, cadastro novo, julgamento...) — add | list | feita | descartada")
    s.add_argument("acao", choices=("list", "add", "feita", "descartada"))
    s.add_argument("--id", type=int); s.add_argument("--tipo", help=" | ".join(TIPOS_TRAVADA))
    s.add_argument("--empresa"); s.add_argument("--titulo"); s.add_argument("--url", help="link da vaga")
    s.add_argument("--url-form", help="link da página/formulário onde parou")
    s.add_argument("--site", help="plataforma (Gupy, Greenhouse, site da empresa...)")
    s.add_argument("--rotina", help="add: quem registrou (ats, linkedin-jobs...) · list: filtra por ela")
    s.add_argument("--fit", type=int); s.add_argument("--etapa", help="onde parou (ex.: 'passo 3/4 — dados pessoais')")
    s.add_argument("--campos", help="campos que faltam, descritos — NUNCA o valor (ex.: 'documento, senha da conta')")
    s.add_argument("--detalhe", help="mensagem literal do site / por que travou"); s.add_argument("--obs", help="o que já foi preenchido, dicas pra você")
    s.add_argument("--candidatura-id", type=int); s.add_argument("--data")
    s.add_argument("--status", help="list: aberta (padrão) | feita | descartada"); s.add_argument("--resolucao")
    s.set_defaults(f=cmd_travada)

    s = sp.add_parser("relatorio", help="resumo do dia em markdown (corpo do e-mail)")
    s.add_argument("--data"); s.set_defaults(f=cmd_relatorio)

    s = sp.add_parser("metricas", help="funil e taxa de resposta/entrevista por fonte (só leitura)")
    s.set_defaults(f=cmd_metricas)

    s = sp.add_parser("followups", help="candidaturas aplicadas/sem-retorno há >= N dias (para follow-up)")
    s.add_argument("--dias", type=int, default=7); s.set_defaults(f=cmd_followups)

    s = sp.add_parser("sql", help="consulta SOMENTE LEITURA"); s.add_argument("consulta"); s.set_defaults(f=cmd_sql)
    s = sp.add_parser("export", help="gera visao/*.md legíveis (só leitura); --csv gera candidaturas.csv")
    s.add_argument("--csv", action="store_true"); s.set_defaults(f=cmd_export)

    a = p.parse_args()
    if a.cmd == "pendencia" and a.acao == "add" and not a.descricao:
        p.error("pendencia add exige --descricao")
    if a.cmd == "travada" and a.acao == "add" and not (a.tipo and (a.url or a.url_form)):
        p.error("travada add exige --tipo e --url (ou --url-form)")
    if a.cmd == "pendencia" and a.acao in ("feita", "descartada") and not a.id:
        p.error(f"pendencia {a.acao} exige --id")
    if a.cmd == "controle" and a.acao == "get" and len(a.pares) != 1:
        p.error("controle get exige 1 chave")
    a.f(a)


if __name__ == "__main__":
    main()
