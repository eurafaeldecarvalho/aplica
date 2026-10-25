#!/usr/bin/env python3
# Aplica — the apply engine's database (SQLite). The agents' only write path:
# never edit the .db by hand. Paths, caps and current employer come from config.py (the user's
# config.json). Help: python jobdb.py -h  |  python jobdb.py <command> -h
import argparse, datetime, io, json, os, re, sqlite3, sys, unicodedata
import config

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DB = config.DB
BACKUPS = config.BACKUPS
KEEP_BACKUPS = 30
# state.db schema version. Stamped in the `control` table on init and verified on check —
# detects drift when a database created by an older engine is opened by a newer one.
# v1 = original Portuguese schema (migrated automatically), v2 = English schema.
SCHEMA_VERSION = "2"

APP_STATUS = ("applied", "uncertain", "test-pending", "in-process", "interview",
              "rejected", "no-reply", "offer", "withdrawn")
SITE_REASONS = ("linkedin-block", "2fa-phone", "captcha-persistent", "email-not-received",
                "google-sso-unavailable", "signup-rejected", "account-exists-bad-password",
                "regional-block", "site-down", "document-required", "paywall", "other")
SITE_STATUS = ("blocked", "resolved", "dismissed")
QUESTION_STATUS = ("pending", "answered", "migrated")
CHANNELS = ("linkedin-dm", "linkedin-connect", "linkedin-comment", "linkedin-interest", "email", "call", "meeting", "other")
# A job the agent could not finish and the user finishes by hand. Never store the VALUE of a
# document/password — only that the field exists.
STUCK_KINDS = ("national-id", "document", "password-login", "new-account", "2fa", "captcha", "payment", "judgment", "other")
OPEN_STATUS = ("open", "done", "dismissed")
DRAFT_KINDS = ("cover-letter", "follow-up", "interview-prep")
DRAFT_STATUS = ("draft", "sent", "archived")
POST_STATUS = ("draft", "approved", "published", "dismissed")


def _in(vals):
    return "(" + ",".join(f"'{v}'" for v in vals) + ")"


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  company TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  source TEXT,
  url TEXT,
  url_norm TEXT,
  key TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN {_in(APP_STATUS)}),
  fit INTEGER,
  resume TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_app_url ON applications(url_norm);
CREATE INDEX IF NOT EXISTS ix_app_key ON applications(key);
CREATE INDEX IF NOT EXISTS ix_app_date ON applications(date);

CREATE TABLE IF NOT EXISTS discards (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  company TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  source TEXT,
  url TEXT,
  url_norm TEXT,
  key TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_disc_url ON discards(url_norm);
CREATE INDEX IF NOT EXISTS ix_disc_key ON discards(key);

CREATE TABLE IF NOT EXISTS legacy_seen (
  url_norm TEXT PRIMARY KEY,
  context TEXT
);

CREATE TABLE IF NOT EXISTS seen_postings (
  key TEXT PRIMARY KEY,
  company TEXT,
  title TEXT,
  url TEXT,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  times INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  question TEXT NOT NULL,
  question_norm TEXT NOT NULL,
  field_type TEXT,
  company TEXT,
  platform TEXT,
  url TEXT,
  agent_answer TEXT,
  official_answer TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN {_in(QUESTION_STATUS)}),
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_q_norm ON questions(question_norm);

CREATE TABLE IF NOT EXISTS blocked_sites (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  site TEXT NOT NULL,
  url TEXT,
  attempting TEXT,
  reason TEXT NOT NULL CHECK (reason IN {_in(SITE_REASONS)}),
  detail TEXT,
  attempts INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'blocked' CHECK (status IN {_in(SITE_STATUS)}),
  resolution TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS people (
  person_norm TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  company TEXT,
  role TEXT,
  profile_url TEXT,
  email TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  person TEXT NOT NULL,
  person_norm TEXT NOT NULL,
  company TEXT,
  channel TEXT NOT NULL CHECK (channel IN {_in(CHANNELS)}),
  direction TEXT NOT NULL CHECK (direction IN ('sent','received')),
  summary TEXT,
  application_id INTEGER REFERENCES applications(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_contact_person ON contacts(person_norm);

CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  description TEXT NOT NULL,
  due TEXT,
  url TEXT,
  application_id INTEGER REFERENCES applications(id),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN {_in(OPEN_STATUS)}),
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS stuck_jobs (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN {_in(STUCK_KINDS)}),
  company TEXT,
  title TEXT,
  key TEXT,
  url TEXT,
  url_norm TEXT NOT NULL DEFAULT '',
  form_url TEXT,
  site TEXT,
  routine TEXT,
  fit INTEGER,
  step TEXT,
  fields TEXT,
  detail TEXT,
  notes TEXT,
  application_id INTEGER REFERENCES applications(id),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN {_in(OPEN_STATUS)}),
  resolution TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_stuck_url ON stuck_jobs(url_norm);
CREATE INDEX IF NOT EXISTS ix_stuck_key ON stuck_jobs(key);

CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN {_in(DRAFT_KINDS)}),
  application_id INTEGER REFERENCES applications(id),
  company TEXT,
  title TEXT,
  path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN {_in(DRAFT_STATUS)}),
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS control (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY,
  run_date TEXT NOT NULL,
  ts TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  kind TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_log_date ON run_log(run_date);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  position INTEGER NOT NULL DEFAULT 100,
  topic TEXT NOT NULL,
  hook TEXT,
  text TEXT NOT NULL,
  image TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN {_in(POST_STATUS)}),
  published_at TEXT,
  url TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT
);
"""
TABLES = ("applications", "discards", "legacy_seen", "seen_postings", "questions", "blocked_sites", "people",
          "contacts", "todos", "stuck_jobs", "drafts", "control", "run_log", "posts")


# ---------- caps / config ----------
def _caps():
    return config.load_config().get("caps", {})


def _current_employer():
    """Normalized forms (letters/digits only) of the current employer (never signal interest there)."""
    return [re.sub(r"[^a-z0-9]", "", slug(e)) for e in config.load_config().get("current_employer", []) if e]


# ---------- normalization ----------
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents(s).lower()).strip("-")


SENIORITY = re.compile(r"\b(senior|sr|pleno|ssr)\b\.?")


# Location/work mode/contract in the title does not change the job — re-posts usually only swap these.
TITLE_NOISE = re.compile(
    r"\b(remote|remoto|remota|work from home|wfh|work|latam|latin america|americas|south america|brazil|brasil|"
    r"worldwide|global|anywhere|usa|us|canada|europe|emea|contract|contractor|freelance|pj|clt|full[ -]?time|"
    r"part[ -]?time|hybrid|hibrido|presencial|on[ -]?site|100)\b")
COMPANY_NOISE = re.compile(r"\b(inc|llc|ltd|ltda|s\.?a|corp|gmbh)\b\.?")


def _title_norm(title):
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", strip_accents(title or "").lower())
    t = SENIORITY.sub(" ", t)
    return slug(TITLE_NOISE.sub(" ", t))


def job_key(company, title):
    comp = COMPANY_NOISE.sub(" ", re.sub(r"\(.*?\)", "", strip_accents(company or "").lower()))
    return f"{slug(comp)}|{_title_norm(title)}"


def _similar(t1, t2):
    a, b = set(t1.split("-")) - {""}, set(t2.split("-")) - {""}
    return bool(a and b) and len(a & b) / len(a | b) >= 0.75


# Query parameters that identify the job (the rest — utm, ref, source — is noise).
ID_PARAMS = {"positionid", "gh_jid", "jobid", "job_id", "jk", "vjk", "id", "jid", "postingid", "requisitionid"}


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
    ids = sorted(p for p in query.split("&") if p.split("=", 1)[0] in ID_PARAMS)
    return base.rstrip("/") + ("?" + "&".join(ids) if ids else "")


def fail(msg, code=1):
    print(f"ERROR {msg}")
    sys.exit(code)


def today():
    return datetime.date.today().isoformat()


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- connection ----------
def connect(create=False, read_only=False):
    if not os.path.exists(DB) and not create:
        print(f"ERROR:db-missing {DB} — do not create an empty database by hand; run `jobdb.py init` or restore from {BACKUPS}")
        sys.exit(1)
    _migrate_if_needed()
    if read_only:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    else:
        con = sqlite3.connect(DB, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def show(rows, cols=None):
    rows = list(rows)
    if not rows:
        print("(none)")
        return
    cols = cols or rows[0].keys()
    print("\t".join(cols))
    for r in rows:
        print("\t".join("" if r[c] is None else str(r[c]).replace("\n", " / ") for c in cols))


def show_json(rows):
    print(json.dumps([dict(r) for r in rows], ensure_ascii=False))


def output(rows, as_json):
    show_json(rows) if as_json else show(rows)


# ---------- migration v1 (Portuguese) → v2 (English) ----------
# Value maps for the enum columns. Unknown values fall back to the column's catch-all.
_M_APP = {"aplicada": "applied", "incerta": "uncertain", "teste-pendente": "test-pending", "em-processo": "in-process",
          "entrevista": "interview", "rejeitada": "rejected", "sem-retorno": "no-reply", "oferta": "offer", "desistiu": "withdrawn"}
_M_REASON = {"linkedin-bloqueio": "linkedin-block", "2fa-celular": "2fa-phone", "captcha-persistente": "captcha-persistent",
             "email-nao-chegou": "email-not-received", "sso-google-indisponivel": "google-sso-unavailable",
             "cadastro-rejeitado": "signup-rejected", "conta-ja-existe-senha-invalida": "account-exists-bad-password",
             "bloqueio-regional": "regional-block", "site-fora-do-ar": "site-down", "exige-documento": "document-required",
             "paywall-assinatura": "paywall", "outro": "other"}
_M_SITE = {"bloqueado": "blocked", "resolvido": "resolved", "descartado": "dismissed"}
_M_Q = {"pendente": "pending", "respondida": "answered", "migrada": "migrated"}
_M_CHANNEL = {"linkedin-dm": "linkedin-dm", "linkedin-conexao": "linkedin-connect", "linkedin-comentario": "linkedin-comment",
              "linkedin-interesse": "linkedin-interest", "email": "email", "outro": "other"}
_M_DIR = {"enviado": "sent", "recebido": "received"}
_M_OPEN = {"aberta": "open", "feita": "done", "descartada": "dismissed"}
_M_STUCK = {"cpf-rg": "national-id", "documento": "document", "senha-login": "password-login", "cadastro-novo": "new-account",
            "2fa": "2fa", "captcha": "captcha", "pagamento": "payment", "julgamento": "judgment", "outro": "other"}
_M_POST = {"rascunho": "draft", "aprovado": "approved", "publicado": "published", "descartado": "dismissed"}

# old table → (new table, {old col: new col}, {new col: (value map, fallback)})
_V1 = {
    "candidaturas": ("applications", {"data": "date", "empresa": "company", "titulo": "title", "fonte": "source", "url": "url",
                                      "url_norm": "url_norm", "chave": "key", "status": "status", "fit": "fit", "obs": "notes",
                                      "criado_em": "created_at", "atualizado_em": "updated_at"},
                     {"status": (_M_APP, "applied")}),
    "descartes": ("discards", {"data": "date", "empresa": "company", "titulo": "title", "fonte": "source", "url": "url",
                               "url_norm": "url_norm", "chave": "key", "motivo": "reason", "criado_em": "created_at"}, {}),
    "vistas_legado": ("legacy_seen", {"url_norm": "url_norm", "contexto": "context"}, {}),
    "perguntas": ("questions", {"data": "date", "pergunta": "question", "pergunta_norm": "question_norm", "tipo_campo": "field_type",
                                "empresa_vaga": "company", "plataforma": "platform", "url": "url", "resposta_agente": "agent_answer",
                                "resposta_oficial": "official_answer", "status": "status", "criado_em": "created_at"},
                  {"status": (_M_Q, "pending")}),
    "sites_bloqueados": ("blocked_sites", {"data": "date", "site": "site", "url": "url", "tentando": "attempting", "motivo": "reason",
                                           "detalhe": "detail", "tentativas": "attempts", "status": "status", "resolucao": "resolution",
                                           "criado_em": "created_at", "atualizado_em": "updated_at"},
                         {"reason": (_M_REASON, "other"), "status": (_M_SITE, "blocked")}),
    "contatos": ("contacts", {"data": "date", "pessoa": "person", "pessoa_norm": "person_norm", "empresa": "company", "canal": "channel",
                              "direcao": "direction", "resumo": "summary", "candidatura_id": "application_id", "criado_em": "created_at"},
                 {"channel": (_M_CHANNEL, "other"), "direction": (_M_DIR, "sent")}),
    "pendencias": ("todos", {"data": "date", "descricao": "description", "prazo": "due", "url": "url", "candidatura_id": "application_id",
                             "status": "status", "criado_em": "created_at", "resolvido_em": "resolved_at"},
                   {"status": (_M_OPEN, "open")}),
    "travadas": ("stuck_jobs", {"data": "date", "tipo": "kind", "empresa": "company", "titulo": "title", "chave": "key", "url": "url",
                                "url_norm": "url_norm", "url_form": "form_url", "site": "site", "rotina": "routine", "fit": "fit",
                                "etapa": "step", "campos": "fields", "detalhe": "detail", "obs": "notes", "candidatura_id": "application_id",
                                "status": "status", "resolucao": "resolution", "criado_em": "created_at", "resolvido_em": "resolved_at"},
                 {"kind": (_M_STUCK, "other"), "status": (_M_OPEN, "open")}),
    "controle": ("control", {"chave": "key", "valor": "value", "atualizado_em": "updated_at"}, {}),
    "sessao_log": ("run_log", {"data_rodada": "run_date", "ts": "ts", "tipo": "kind", "texto": "text"}, {}),
    "posts": ("posts", {"ordem": "position", "tema": "topic", "gancho": "hook", "texto": "text", "imagem": "image", "status": "status",
                        "publicado_em": "published_at", "url": "url", "obs": "notes", "criado_em": "created_at", "atualizado_em": "updated_at"},
              {"status": (_M_POST, "draft")}),
}


def _is_v1():
    """Cheap READ-ONLY check: does this DB still have the v1 `candidaturas` table? No write side effect,
    so a normal read of an already-v2 DB never opens a write connection or touches backups/."""
    try:
        ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
        try:
            return ro.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidaturas'").fetchone() is not None
        finally:
            ro.close()
    except sqlite3.Error:
        return False


def _migrate_if_needed():
    """Upgrade a v1 (Portuguese) state.db in place to the v2 English schema. Idempotent; takes a
    backup first and runs in one transaction, so a failure leaves the original untouched.
    Only opens a write connection when a v1 DB is actually present (checked read-only first), so a
    normal read against a v2 DB has no write side effect."""
    if not os.path.exists(DB) or not _is_v1():
        return
    con = sqlite3.connect(DB, timeout=30, isolation_level=None)  # manual BEGIN/COMMIT (DDL included)
    try:
        # Back up the pristine v1 DB BEFORE taking the write lock (con.backup deadlocks if the source
        # connection already holds an open write transaction). In the rare concurrent-first-run case
        # this may write a backup we then discard — harmless.
        os.makedirs(BACKUPS, exist_ok=True)
        with sqlite3.connect(os.path.join(BACKUPS, f"state-v1-{datetime.datetime.now():%Y-%m-%d_%H%M%S}.db")) as dst:
            con.backup(dst)
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN IMMEDIATE")
        # re-check INSIDE the transaction: another process may have migrated while we waited for the
        # write lock (concurrent first run). If `candidaturas` is gone, there is nothing to do.
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "candidaturas" not in names:
            con.execute("COMMIT")
            return
        # the v1 `posts` table shares its name with v2 — move it aside first
        if "posts" in names:
            con.execute("ALTER TABLE posts RENAME TO posts_v1")
        for stmt in SCHEMA.split(";"):
            if stmt.strip():
                con.execute(stmt)
        for old, (new, cols, maps) in _V1.items():
            src = "posts_v1" if old == "posts" else old
            if src not in {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
                continue
            have = {r[1] for r in con.execute(f"PRAGMA table_info({src})")}
            pairs = [(o, n) for o, n in cols.items() if o in have]
            id_col = "id" in have and old not in ("vistas_legado", "controle")
            sel = (["id"] if id_col else []) + [o for o, _ in pairs]
            ins = (["id"] if id_col else []) + [n for _, n in pairs]
            for r in con.execute(f"SELECT {','.join(sel)} FROM {src}").fetchall():
                vals = dict(zip(ins, r))
                for col, (m, fb) in maps.items():
                    if col in vals:
                        vals[col] = m.get(vals[col], fb)
                if new == "control" and vals.get("key") == "NAVEGADOR_LOCK":
                    vals["key"] = LOCK
                con.execute(f"INSERT OR REPLACE INTO {new} ({','.join(vals)}) VALUES ({','.join('?' * len(vals))})",
                            list(vals.values()))
            con.execute(f"DROP TABLE {src}")
        if "historico" in names:
            con.execute("DROP TABLE historico")
        # the v1 schema had no people table — backfill it from the migrated contacts so the CRM
        # view shows everyone the agent ever talked to (interest pings excluded; they have no person)
        con.execute(
            "INSERT OR IGNORE INTO people (person_norm,name,company) "
            "SELECT person_norm, person, (SELECT company FROM contacts c2 WHERE c2.person_norm=c.person_norm "
            "  AND company IS NOT NULL ORDER BY date DESC LIMIT 1) "
            "FROM contacts c WHERE channel<>'linkedin-interest' GROUP BY person_norm")
        con.execute("INSERT INTO control (key,value) VALUES ('schema_version',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (SCHEMA_VERSION,))
        con.execute("COMMIT")
        print(f"migrated state.db from schema v1 to v{SCHEMA_VERSION} (backup in {BACKUPS})", file=sys.stderr)
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()


# ---------- dedup ----------
def seen_urls(con):
    q = """SELECT url_norm FROM applications WHERE url_norm <> ''
           UNION SELECT url_norm FROM discards WHERE url_norm <> ''
           UNION SELECT url_norm FROM stuck_jobs WHERE url_norm <> ''
           UNION SELECT url_norm FROM legacy_seen"""
    return {r[0] for r in con.execute(q)}


def dedup(con, url, company, title):
    un = norm_url(url)
    if un:
        r = con.execute("SELECT id,status,date FROM applications WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"DUPLICATE application id={r['id']} status={r['status']} date={r['date']} (same URL)"
        r = con.execute("SELECT id,date,reason FROM discards WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"DISCARDED-BEFORE id={r['id']} date={r['date']} reason={(r['reason'] or '')[:120]}"
        r = con.execute("SELECT id,date,kind,status FROM stuck_jobs WHERE url_norm=? LIMIT 1", (un,)).fetchone()
        if r:
            return f"STUCK id={r['id']} kind={r['kind']} status={r['status']} date={r['date']} (already on your list — skip)"
        r = con.execute("SELECT context FROM legacy_seen WHERE url_norm=?", (un,)).fetchone()
        if r:
            return f"LEGACY-SEEN (URL cited in an old import: {(r['context'] or '')[:120]})"
    if company:
        k = job_key(company, title)
        r = con.execute("SELECT id,status,date FROM applications WHERE key=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"DUPLICATE application id={r['id']} status={r['status']} date={r['date']} (same company+role)"
        r = con.execute("SELECT id,date,reason FROM discards WHERE key=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"DISCARDED-BEFORE id={r['id']} date={r['date']} reason={(r['reason'] or '')[:120]}"
        r = con.execute("SELECT id,date,kind,status FROM stuck_jobs WHERE key=? LIMIT 1", (k,)).fetchone()
        if r:
            return f"STUCK id={r['id']} kind={r['kind']} status={r['status']} date={r['date']} (same company+role; already on your list — skip)"
        comp, _, tit = k.partition("|")
        for r in con.execute("SELECT id,status,date,title,key FROM applications WHERE key LIKE ?", (comp + "|%",)):
            if _similar(tit, r["key"].partition("|")[2]):
                return f"DUPLICATE application id={r['id']} status={r['status']} date={r['date']} (same company, equivalent title: \"{r['title']}\")"
    return "NEW"


# ---------- ghost jobs: how often a posting has been seen ----------
def record_seen(con, company, title, url=""):
    """Scanner hook: count one sighting of company+title (at most once per day)."""
    k, d = job_key(company, title), today()
    r = con.execute("SELECT last_seen FROM seen_postings WHERE key=?", (k,)).fetchone()
    if not r:
        con.execute("INSERT INTO seen_postings (key,company,title,url,first_seen,last_seen) VALUES (?,?,?,?,?,?)",
                    (k, company, title, url, d, d))
    elif r[0] != d:
        con.execute("UPDATE seen_postings SET last_seen=?, times=times+1, url=COALESCE(?,url) WHERE key=?", (d, url or None, k))


def seen_stats(con, company, title):
    """(times seen, days between first and last sighting) for company+title."""
    r = con.execute("SELECT first_seen,last_seen,times FROM seen_postings WHERE key=?", (job_key(company, title),)).fetchone()
    if not r:
        return 1, 0
    span = (datetime.date.fromisoformat(r["last_seen"]) - datetime.date.fromisoformat(r["first_seen"])).days
    return r["times"], span


# ---------- commands ----------
def _create_db():
    """Create the schema (idempotent) and stamp the version. The plugin ships its own database."""
    con = connect(create=True)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO control (key,value) VALUES ('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (SCHEMA_VERSION,))
    con.commit()
    return con


def cmd_init(a):
    _create_db()
    print(f"OK schema at {DB} (schema_version={SCHEMA_VERSION})")


def cmd_check(a):
    # First run: the plugin creates its own database automatically, isolated in the config dir
    # (APLICA_HOME / ~/.config/aplica), never pointing at a database that already exists on the machine.
    if not os.path.exists(DB):
        try:
            _create_db()
            print(f"database created automatically at {DB}")
        except sqlite3.Error as e:
            print(f"ERROR:db-create {e}")
            sys.exit(1)
    try:
        con = connect()
        con.executescript(SCHEMA)  # additive: tables added in a later version appear on check
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            print(f"ERROR:integrity {ok}")
            sys.exit(1)
        existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in TABLES if t not in existing]
        if missing:
            print(f"ERROR:missing-tables {','.join(missing)}")
            sys.exit(1)
        for t in TABLES:
            print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
        r = con.execute("SELECT value FROM control WHERE key='schema_version'").fetchone()
        ver = r[0] if r else None
        if ver and ver != SCHEMA_VERSION:
            print(f"WARNING:schema-version db={ver} engine={SCHEMA_VERSION} (drift between engine copies — resync)")
    except sqlite3.Error as e:
        print(f"ERROR:sqlite {e}")
        sys.exit(1)
    print("OK")


def cmd_backup(a):
    con = connect()
    os.makedirs(BACKUPS, exist_ok=True)
    dest = os.path.join(BACKUPS, f"state-{datetime.datetime.now():%Y-%m-%d_%H%M}.db")
    with sqlite3.connect(dest) as dst:
        con.backup(dst)
    old = sorted(f for f in os.listdir(BACKUPS) if f.startswith("state-") and f.endswith(".db") and not f.startswith("state-v1-"))
    for f in old[:-KEEP_BACKUPS]:
        os.remove(os.path.join(BACKUPS, f))
    print(f"OK {dest}")


def cmd_dedup(a):
    print(dedup(connect(read_only=True), a.url, a.company, a.title))


def cmd_add_application(a):
    if a.status not in APP_STATUS:
        fail(f"invalid status: {a.status} (valid: {', '.join(APP_STATUS)})")
    con = connect()
    d = dedup(con, a.url, a.company, a.title)
    if d != "NEW":
        print(d)
        if d.startswith("DISCARDED-BEFORE"):
            print("NOT-SAVED — job already discarded at the gate; --force does not apply (only you can reverse a discard)")
            sys.exit(2)
        if not a.force:
            print("NOT-SAVED (use --force --force-reason \"..\" only for a genuinely different job)")
            sys.exit(2)
        if not a.force_reason:
            fail("--force requires --force-reason explaining why it is a different job", 2)
    _block_secret(a.notes)
    cur = con.execute(
        "INSERT INTO applications (date,company,title,source,url,url_norm,key,status,fit,resume,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (a.date or today(), a.company, a.title or "", a.source, a.url, norm_url(a.url),
         job_key(a.company, a.title), a.status, a.fit, a.resume, a.notes))
    if a.force and d != "NEW":
        con.execute("INSERT INTO todos (date,description,url,application_id) VALUES (?,?,?,?)",
                    (today(), f"Review FORCED application id={cur.lastrowid} ({a.company} — {a.title}): {a.force_reason} | dedup said: {d[:150]}",
                     a.url, cur.lastrowid))
    con.commit()
    print(f"OK application id={cur.lastrowid}")


def cmd_update_application(a):
    con = connect()
    if a.id:
        r = con.execute("SELECT * FROM applications WHERE id=?", (a.id,)).fetchone()
    elif a.url:
        r = con.execute("SELECT * FROM applications WHERE url_norm=? ORDER BY id DESC LIMIT 1", (norm_url(a.url),)).fetchone()
    else:
        fail("pass --id or --url")
    if not r:
        fail("application not found")
    status = a.status or r["status"]
    if status not in APP_STATUS:
        fail(f"invalid status: {status}")
    _block_secret(a.notes_append)
    notes = r["notes"] or ""
    if a.notes_append:
        notes = (notes + "\n" if notes else "") + f"[{today()}] {a.notes_append}"
    elif a.status and a.status != r["status"]:
        notes = (notes + "\n" if notes else "") + f"[{today()}] status {r['status']} → {a.status}"
    fit = a.fit if a.fit is not None else r["fit"]
    con.execute("UPDATE applications SET status=?, notes=?, fit=?, updated_at=datetime('now','localtime') WHERE id=?",
                (status, notes, fit, r["id"]))
    con.commit()
    print(f"OK application id={r['id']} status={status}")


def cmd_add_discard(a):
    _block_secret(a.reason)
    con = connect()
    cur = con.execute(
        "INSERT INTO discards (date,company,title,source,url,url_norm,key,reason) VALUES (?,?,?,?,?,?,?,?)",
        (a.date or today(), a.company, a.title or "", a.source, a.url, norm_url(a.url), job_key(a.company, a.title), a.reason))
    con.commit()
    print(f"OK discard id={cur.lastrowid}")


def cmd_applications(a):
    con = connect(read_only=True)
    where, args = [], []
    if a.date:
        where.append("date=?"); args.append(a.date)
    if a.status:
        where.append("status=?"); args.append(a.status)
    if a.search:
        where.append("(company LIKE ? OR title LIKE ? OR notes LIKE ?)"); args += [f"%{a.search}%"] * 3
    cols = "id,date,company,title,source,status,fit,resume,url" + (",notes,updated_at" if a.json else "")
    sql = f"SELECT {cols} FROM applications"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY date DESC, id DESC LIMIT {int(a.limit)}"
    output(con.execute(sql, args), a.json)


def cmd_today(a):
    con = connect(read_only=True)
    d = a.date or today()
    n = con.execute("SELECT COUNT(*) FROM applications WHERE date=? AND status<>'uncertain'", (d,)).fetchone()[0]
    print(f"APPLICATIONS_COUNTED={n}")
    show(con.execute("SELECT id,company,title,status,url FROM applications WHERE date=? ORDER BY id", (d,)))


def cmd_add_question(a):
    _block_secret(a.question, a.agent_answer)
    con = connect()
    qn = slug(a.question)
    r = con.execute("SELECT id,company FROM questions WHERE question_norm=?", (qn,)).fetchone()
    if r:
        if a.company and a.company not in (r["company"] or ""):
            con.execute("UPDATE questions SET company=? WHERE id=?",
                        (((r["company"] or "") + "; " + a.company).strip("; "), r["id"]))
            con.commit()
        print(f"EXISTING question id={r['id']} (occurrence added)")
        return
    cur = con.execute(
        "INSERT INTO questions (date,question,question_norm,field_type,company,platform,url,agent_answer) VALUES (?,?,?,?,?,?,?,?)",
        (a.date or today(), a.question, qn, a.field_type, a.company, a.platform, a.url, a.agent_answer))
    con.commit()
    print(f"OK question id={cur.lastrowid}")


def cmd_questions(a):
    con = connect(read_only=True)
    sql, args = "SELECT id,date,status,question,agent_answer,official_answer FROM questions", []
    if a.answered:
        sql += " WHERE official_answer IS NOT NULL AND official_answer<>''"
    elif a.status in QUESTION_STATUS:
        sql, args = sql + " WHERE status=?", [a.status]
    output(con.execute(sql + " ORDER BY id", args), a.json)


def cmd_answer_question(a):
    _block_secret(a.answer)  # official_answer is surfaced in `context` JSON (drafts grounding) — never store a secret
    con = connect()
    n = con.execute("UPDATE questions SET official_answer=?, status='answered' WHERE id=?", (a.answer, a.id)).rowcount
    con.commit()
    if not n:
        fail(f"question id={a.id} does not exist")
    print(f"OK question id={a.id} answered")


def cmd_add_site(a):
    if a.reason not in SITE_REASONS:
        fail(f"invalid reason: {a.reason} (valid: {', '.join(SITE_REASONS)})")
    _block_secret(a.detail, a.attempting)
    con = connect()
    r = con.execute("SELECT id,attempts FROM blocked_sites WHERE lower(site)=lower(?) AND status='blocked' ORDER BY id DESC LIMIT 1",
                    (a.site,)).fetchone()
    if r:
        con.execute("UPDATE blocked_sites SET attempts=attempts+1, date=?, reason=?, detail=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (a.date or today(), a.reason, a.detail, r["id"]))
        con.commit()
        print(f"OK site id={r['id']} attempts={r['attempts'] + 1}")
        return
    cur = con.execute("INSERT INTO blocked_sites (date,site,url,attempting,reason,detail) VALUES (?,?,?,?,?,?)",
                      (a.date or today(), a.site, a.url, a.attempting, a.reason, a.detail))
    con.commit()
    print(f"OK site id={cur.lastrowid}")


def cmd_update_site(a):
    if a.status and a.status not in SITE_STATUS:
        fail(f"invalid status: {a.status}")
    _block_secret(a.resolution)
    con = connect()
    n = con.execute("UPDATE blocked_sites SET status=COALESCE(?,status), resolution=COALESCE(?,resolution), updated_at=datetime('now','localtime') WHERE id=?",
                    (a.status, a.resolution, a.id)).rowcount
    con.commit()
    if not n:
        fail(f"site id={a.id} does not exist")
    print(f"OK site id={a.id}")


def cooldown(reason, attempts, date):
    if reason not in ("linkedin-block", "captcha-persistent"):
        return ""
    if attempts >= 3:
        return "disabled — needs you"
    hours = 24 if attempts <= 1 else 72
    try:
        end = datetime.datetime.fromisoformat(date) + datetime.timedelta(hours=hours)
        return f"cooldown until {end:%Y-%m-%d}" if end > datetime.datetime.now() else "cooldown over"
    except ValueError:
        return ""


def cmd_active_sites(a):
    con = connect(read_only=True)
    rows = con.execute("SELECT id,date,site,reason,attempts,status FROM blocked_sites WHERE status IN ('blocked','dismissed') ORDER BY site").fetchall()
    if not rows:
        print("(none)")
    for r in rows:
        print(f"{r['id']}\t{r['site']}\t{r['status']}\t{r['reason']}\tattempts={r['attempts']}\t{r['date']}\t{cooldown(r['reason'], r['attempts'], r['date'])}")


def _upsert_person(con, name, company=None, role=None, profile_url=None, email=None, notes=None):
    pn = slug(name)
    con.execute(
        "INSERT INTO people (person_norm,name,company,role,profile_url,email,notes) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(person_norm) DO UPDATE SET company=COALESCE(excluded.company,company), role=COALESCE(excluded.role,role), "
        "profile_url=COALESCE(excluded.profile_url,profile_url), email=COALESCE(excluded.email,email), "
        "notes=COALESCE(excluded.notes,notes), updated_at=datetime('now','localtime')",
        (pn, name, company, role, profile_url, email, notes))
    return pn


def cmd_add_contact(a):
    if a.channel not in CHANNELS:
        fail(f"invalid channel: {a.channel} (valid: {', '.join(CHANNELS)})")
    _block_secret(a.summary)
    con = connect()
    # "I'm interested" is logged against a company page, not a person — keep it out of the CRM
    if a.channel != "linkedin-interest":
        _upsert_person(con, a.person, company=a.company)
    cur = con.execute("INSERT INTO contacts (date,person,person_norm,company,channel,direction,summary,application_id) VALUES (?,?,?,?,?,?,?,?)",
                      (a.date or today(), a.person, slug(a.person), a.company, a.channel, a.direction, a.summary, a.application_id))
    con.commit()
    print(f"OK contact id={cur.lastrowid}")


def cmd_person(a):
    """CRM: upsert a person's details (company, role, links, notes)."""
    _block_secret(a.notes)
    con = connect()
    pn = _upsert_person(con, a.name, a.company, a.role, a.profile_url, a.email, a.notes)
    con.commit()
    print(f"OK person {pn}")


def cmd_contacts(a):
    """CRM: one row per person — last touch, counts, linked application."""
    con = connect(read_only=True)
    sql = """
      WITH agg AS (
        SELECT person_norm, MAX(date) AS last_date, COUNT(*) AS touches,
               SUM(direction='sent') AS sent, SUM(direction='received') AS received,
               MAX(application_id) AS application_id
        FROM contacts WHERE channel<>'linkedin-interest' GROUP BY person_norm)
      SELECT p.person_norm AS id, p.name, COALESCE(p.company,
               (SELECT company FROM contacts c WHERE c.person_norm=p.person_norm AND company IS NOT NULL ORDER BY date DESC LIMIT 1)) AS company,
             p.role, p.profile_url, p.email, p.notes,
             agg.last_date, COALESCE(agg.touches,0) AS touches, COALESCE(agg.sent,0) AS sent, COALESCE(agg.received,0) AS received,
             (SELECT channel || ' · ' || direction || COALESCE(' — ' || summary,'') FROM contacts c WHERE c.person_norm=p.person_norm
               ORDER BY date DESC, id DESC LIMIT 1) AS last_touch,
             agg.application_id
      FROM people p LEFT JOIN agg ON agg.person_norm=p.person_norm"""
    args = []
    if a.search:
        sql += " WHERE p.name LIKE ? OR p.company LIKE ? OR p.notes LIKE ?"
        args = [f"%{a.search}%"] * 3
    sql += " ORDER BY COALESCE(agg.last_date,'0000') DESC, p.name"
    output(con.execute(sql, args), a.json)


def cmd_contact_history(a):
    con = connect(read_only=True)
    output(con.execute("SELECT id,date,channel,direction,company,summary,application_id FROM contacts WHERE person_norm=? ORDER BY date DESC, id DESC",
                       (slug(a.person),)), a.json)


def cmd_recent_contact(a):
    con = connect(read_only=True)
    since = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    flt, args = "", [slug(a.person), since]
    if a.channel:
        flt, args = " AND channel=?", args + [a.channel]
    r = con.execute("SELECT date,channel,summary FROM contacts WHERE person_norm=? AND direction='sent' AND date>=?" + flt +
                    " ORDER BY date DESC LIMIT 1", args).fetchone()
    if r:
        print(f"YES {r['date']} {r['channel']} — {(r['summary'] or '')[:120]}")
        return
    # older records (before the contacts table) only exist as text in the application notes
    extra = " AND (notes LIKE '%DM%' OR source LIKE '%Messag%')" if a.channel == "linkedin-dm" else ""
    r = con.execute("SELECT id,date FROM applications WHERE date>=? AND (company LIKE ? OR notes LIKE ?)" + extra +
                    " ORDER BY date DESC LIMIT 1", (since, f"%{a.person}%", f"%{a.person}%")).fetchone()
    if r:
        print(f"POSSIBLE name cited in application id={r['id']} on {r['date']} — treat as YES")
        return
    print("NO")


def cmd_social_today(a):
    con = connect(read_only=True)
    cap = int(_caps().get("social_per_day", 0))
    n = con.execute("SELECT COUNT(*) FROM contacts WHERE direction='sent' AND channel LIKE 'linkedin-%' AND channel<>'linkedin-interest' AND date=?",
                    (today(),)).fetchone()[0]
    print(f"SOCIAL_TODAY={n} CAP={cap} REMAINING={max(0, cap - n)}")


def cmd_interest_check(a):
    """May we click "I'm interested" on the company page? Once every N days per company, daily cap, never the current employer."""
    con = connect(read_only=True)
    cap = int(_caps().get("interest_per_day", 0))
    cooldown_days = int(_caps().get("interest_cooldown_days", 180))
    employer = _current_employer()
    comp = slug(a.company)
    comp_alnum = re.sub(r"[^a-z0-9]", "", comp)
    if any(e and e in comp_alnum for e in employer):
        print("NO current-employer")
        return
    n = con.execute("SELECT COUNT(*) FROM contacts WHERE direction='sent' AND channel='linkedin-interest' AND date=?",
                    (today(),)).fetchone()[0]
    if n >= cap:
        print(f"NO daily-cap ({n}/{cap})")
        return
    since = (datetime.date.today() - datetime.timedelta(days=cooldown_days)).isoformat()
    r = con.execute("SELECT date FROM contacts WHERE channel='linkedin-interest' AND direction='sent' AND person_norm=? AND date>=? ORDER BY date DESC LIMIT 1",
                    (comp, since)).fetchone()
    if r:
        print(f"NO already-signaled {r['date']}")
        return
    print(f"YES (today {n}/{cap})")


def cmd_interest_pending(a):
    """Companies with a high-fit (or in-process) application in the last N days that have not received "I'm interested" yet."""
    con = connect(read_only=True)
    cooldown_days = int(_caps().get("interest_cooldown_days", 180))
    employer = _current_employer()
    since = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    since_cd = (datetime.date.today() - datetime.timedelta(days=cooldown_days)).isoformat()
    done = {r[0] for r in con.execute("SELECT person_norm FROM contacts WHERE channel='linkedin-interest' AND direction='sent' AND date>=?", (since_cd,))}
    rows = con.execute("SELECT id,date,company,title,fit,status FROM applications WHERE date>=? AND status NOT IN ('rejected','withdrawn','uncertain') "
                       "AND (fit>=? OR status IN ('in-process','interview','test-pending')) ORDER BY COALESCE(fit,0) DESC, date DESC",
                       (since, a.min_fit)).fetchall()
    seen, n = set(), 0
    for r in rows:
        comp = slug(r["company"])
        comp_alnum = re.sub(r"[^a-z0-9]", "", comp)
        if comp in done or comp in seen or any(e and e in comp_alnum for e in employer):
            continue
        seen.add(comp)
        print(f"{r['company']}\tapplication={r['id']}\tfit={r['fit']}\t{r['status']}\t{r['date']}\t{r['title']}")
        n += 1
        if n >= a.limit:
            break
    if not n:
        print("(none)")


def _read_text(a):
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            return f.read().strip()
    return (a.text or "").strip()


def cmd_add_post(a):
    text = _read_text(a)
    if not text:
        fail("empty text (use --file or --text)")
    _block_secret(text, a.hook, a.notes)  # hook is published externally (post-next/show) — guard it too
    if a.image and not os.path.exists(a.image):
        fail(f"image does not exist: {a.image}")
    con = connect()
    cur = con.execute("INSERT INTO posts (position,topic,hook,text,image,notes) VALUES (?,?,?,?,?,?)",
                      (a.position, a.topic, a.hook, text, a.image, a.notes))
    con.commit()
    print(f"OK post id={cur.lastrowid} status=draft ({len(text)} characters)")


def cmd_posts(a):
    con = connect(read_only=True)
    q, args = "SELECT id,position,status,topic,hook,length(text) AS chars,CASE WHEN image IS NULL THEN '' ELSE 'yes' END AS img,published_at FROM posts", []
    if a.status:
        q, args = q + " WHERE status=?", [a.status]
    show(con.execute(q + " ORDER BY CASE status WHEN 'published' THEN 1 ELSE 0 END, position, id", args))


def cmd_post_show(a):
    con = connect(read_only=True)
    r = con.execute("SELECT * FROM posts WHERE id=?", (a.id,)).fetchone()
    if not r:
        fail(f"post {a.id} does not exist")
    print(f"# post {r['id']} — {r['status']} — topic: {r['topic']} — hook: {r['hook']} — image: {r['image'] or 'none'}")
    print(r["text"])


def cmd_post_status(a):
    _block_secret(a.notes)
    con = connect()
    n = con.execute("UPDATE posts SET status=?, notes=COALESCE(notes||' | ','')||COALESCE(?,''), updated_at=datetime('now','localtime') WHERE id=?",
                    (a.status, a.notes, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} → {a.status}" if n else f"ERROR post {a.id} does not exist")


def cmd_post_edit(a):
    text = _read_text(a)
    if not text:
        fail("empty text")
    _block_secret(text)
    con = connect()
    n = con.execute("UPDATE posts SET text=?, status='draft', updated_at=datetime('now','localtime') WHERE id=? AND status<>'published'",
                    (text, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} updated (back to draft — needs approval again)" if n else "ERROR post missing or already published")


def cmd_post_next(a):
    """Routine: is there a post to publish today? Only 'approved', only if the last one was published >= INTERVAL days ago."""
    con = connect(read_only=True)
    interval = int(_caps().get("post_interval_days", 7))
    last = con.execute("SELECT MAX(published_at) FROM posts WHERE status='published'").fetchone()[0]
    if last:
        nxt = datetime.date.fromisoformat(last[:10]) + datetime.timedelta(days=interval)
        if datetime.date.today() < nxt:
            print(f"WAIT next on {nxt.isoformat()} (last published {last[:10]})")
            return
    r = con.execute("SELECT * FROM posts WHERE status='approved' ORDER BY position, id LIMIT 1").fetchone()
    if not r:
        print("QUEUE_EMPTY (no approved post)")
        return
    print(f"PUBLISH id={r['id']} image={r['image'] or 'none'}")
    print("-----")
    print(r["text"])


def cmd_post_published(a):
    con = connect()
    n = con.execute("UPDATE posts SET status='published', published_at=?, url=?, updated_at=datetime('now','localtime') WHERE id=? AND status='approved'",
                    (now(), a.url, a.id)).rowcount
    con.commit()
    print(f"OK post {a.id} published" if n else f"ERROR post {a.id} is not 'approved'")


def cmd_linkedin_status(a):
    con = connect(read_only=True)
    r = con.execute("SELECT date,detail FROM blocked_sites WHERE reason='linkedin-block' AND status='blocked' ORDER BY date DESC LIMIT 1").fetchone()
    print(f"BLOCKED since {r['date']} — only resumes once you mark it resolved ({(r['detail'] or '')[:100]})" if r else "OK")


LOCK = "BROWSER_LOCK"


def cmd_lock(a):
    if a.action == "wait":
        # Wait INSIDE the call (a routine cannot end its turn to wait: a scheduled run does not wake up again).
        import subprocess, time
        end = time.time() + a.minutes * 60
        while True:
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "lock", "acquire", "--owner", a.owner,
                                "--ttl-min", str(a.ttl_min)], capture_output=True, text=True, encoding="utf-8")
            if r.returncode == 0:
                print(r.stdout.strip())
                return
            if time.time() + 30 > end:
                print(r.stdout.strip() + f" — still busy after {a.minutes} min")
                sys.exit(3)
            time.sleep(30)
    con = connect()
    con.execute("BEGIN IMMEDIATE")
    r = con.execute("SELECT value FROM control WHERE key=?", (LOCK,)).fetchone()
    now_dt = datetime.datetime.now()
    holder, since = None, None
    if r and r[0]:
        holder, _, ts = r[0].partition("|")
        since = datetime.datetime.fromisoformat(ts)
    if a.action == "check":
        con.rollback()
        if holder == a.owner:
            print(f"OK lock held by {a.owner}")
            return
        print(f"STOP: the lock no longer belongs to {a.owner} (now: {holder or 'nobody'}) — the run that started you has ended")
        sys.exit(4)
    if a.action == "acquire":
        expired = since is None or now_dt - since > datetime.timedelta(minutes=a.ttl_min)
        if holder and holder != a.owner and not expired:
            con.rollback()
            print(f"BUSY held by {holder} since {since:%H:%M}")
            sys.exit(3)
        con.execute("INSERT INTO control (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now','localtime')",
                    (LOCK, f"{a.owner}|{now_dt:%Y-%m-%dT%H:%M:%S}"))
        con.commit()
        print(f"OK lock={a.owner}" + (f" (taken from {holder}, expired)" if holder and holder != a.owner else ""))
    else:
        if holder == a.owner:
            con.execute("DELETE FROM control WHERE key=?", (LOCK,))
        con.commit()
        print("OK released" if holder == a.owner else f"OK (lock belonged to {holder or 'nobody'}, nothing done)")


def cmd_control(a):
    if a.action == "show":
        show(connect(read_only=True).execute("SELECT key,value,updated_at FROM control ORDER BY key"))
    elif a.action == "get":
        r = connect(read_only=True).execute("SELECT value FROM control WHERE key=?", (a.pairs[0],)).fetchone()
        print(r[0] if r else "")
    elif a.action == "set":
        con = connect()
        for p in a.pairs:
            if "=" not in p:
                fail(f"use KEY=value (got {p})")
            k, v = p.split("=", 1)
            if v == "":
                con.execute("DELETE FROM control WHERE key=?", (k.strip(),))
            else:
                con.execute("INSERT INTO control (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now','localtime')",
                            (k.strip(), v))
        con.commit()
        print("OK")


def cmd_log(a):
    _block_secret(a.text)
    con = connect()
    con.execute("INSERT INTO run_log (run_date,kind,text) VALUES (?,?,?)", (a.run_date or today(), a.kind, a.text))
    con.commit()
    print("OK")


def cmd_logs(a):
    show(connect(read_only=True).execute(
        "SELECT ts,kind,text FROM run_log WHERE run_date=? ORDER BY id", (a.date or today(),)))


def cmd_todo(a):
    con = connect()
    if a.action == "add":
        _block_secret(a.description)
        open_rows = con.execute("SELECT id,description,url FROM todos WHERE status='open'").fetchall()
        un = norm_url(a.url)
        for p in open_rows:
            if (un and norm_url(p["url"]) == un) or _similar(slug(p["description"])[:120], slug(a.description)[:120]):
                print(f"EXISTING todo id={p['id']} (already open: {p['description'][:100]})")
                return
        cur = con.execute("INSERT INTO todos (date,description,due,url,application_id) VALUES (?,?,?,?,?)",
                          (today(), a.description, a.due, a.url, a.application_id))
        con.commit()
        print(f"OK todo id={cur.lastrowid}")
    elif a.action in ("done", "dismiss"):
        st = "done" if a.action == "done" else "dismissed"
        con.execute("UPDATE todos SET status=?, resolved_at=datetime('now','localtime') WHERE id=?", (st, a.id))
        con.commit()
        print(f"OK todo id={a.id} {st}")
    else:
        output(con.execute("SELECT id,date,due,description,url,application_id FROM todos WHERE status='open' ORDER BY COALESCE(due,'9999'), id"), a.json)


# Anti-secret guard: never store the VALUE of a document, card or password — only the field's
# description. HIGH-PRECISION safety net (the agent is already told never to store secrets): it
# only blocks what is clearly a secret, so legitimate text such as a bare phone number, a date or
# an id is never rejected. Applied to every free-text field at write time.
# ACCEPTED LIMITATION (low recall by design): a bare, unlabeled 11-digit CPF (e.g. "12345678901")
# is NOT caught — it is indistinguishable from a phone number, and rejecting it would produce false
# positives on legitimate text. This guard is a backstop, not the primary control: the primary
# control is the agent instruction to never write a secret. It DOES catch a formatted CPF, a
# labeled national ID (cpf/rg/passport ... <digits>), a labeled password/token, and a Luhn-valid card.
LOOKS_LIKE_DOC = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")   # FORMATTED Brazilian CPF (punctuation required)
LOOKS_LIKE_ID = re.compile(r"\b(cpf|rg|passport|passaporte|national\s*id|ssn)\b\s*(?:n[oº.]*)?\s*[:=#]?\s*(?:\d[\d.\- ]{6,})", re.I)  # labeled national-ID value
LOOKS_LIKE_PASSWORD = re.compile(r"\b(senha|password|passwd|pwd|secret|token|api[_-]?key)\b\s*[:=]\s*\S+", re.I)
_LONG_SEQ = re.compile(r"(?:\d[ -]?){13,19}")                   # card candidate (validated by Luhn)


def _luhn_ok(digits):
    d = [int(c) for c in digits]
    if not (13 <= len(d) <= 19):
        return False
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2 == 1:
            x *= 2
            if x > 9:
                x -= 9
        s += x
    return s % 10 == 0


def _secret_in(*fields):
    """The reason if any field looks like it holds a real secret, else None."""
    for c in fields:
        if not c:
            continue
        if LOOKS_LIKE_DOC.search(c) or LOOKS_LIKE_ID.search(c):
            return "a national ID value (CPF/RG/passport)"
        if LOOKS_LIKE_PASSWORD.search(c):
            return "a plain-text password/token"
        for m in _LONG_SEQ.finditer(c):
            if _luhn_ok(re.sub(r"\D", "", m.group())):
                return "a card number (Luhn-valid)"
    return None


def _block_secret(*fields):
    m = _secret_in(*fields)
    if m:
        fail(f"text seems to contain {m} — describe the field (e.g. \"national ID required\"), never store the value")


def cmd_stuck(a):
    con = connect()
    if a.action == "add":
        if a.kind not in STUCK_KINDS:
            fail(f"invalid kind: {a.kind} (valid: {', '.join(STUCK_KINDS)})")
        _block_secret(a.fields, a.detail, a.notes, a.step)
        un = norm_url(a.url)
        k = job_key(a.company, a.title) if a.company else None
        r = None
        if un:
            r = con.execute("SELECT id,kind FROM stuck_jobs WHERE url_norm=? AND status='open' LIMIT 1", (un,)).fetchone()
        if not r and k:
            r = con.execute("SELECT id,kind FROM stuck_jobs WHERE key=? AND status='open' LIMIT 1", (k,)).fetchone()
        if r:
            print(f"EXISTING stuck id={r['id']} kind={r['kind']} (already open)")
            return
        cur = con.execute(
            "INSERT INTO stuck_jobs (date,kind,company,title,key,url,url_norm,form_url,site,routine,fit,step,fields,detail,notes,application_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (a.date or today(), a.kind, a.company, a.title, k, a.url, un, a.form_url, a.site, a.routine, a.fit,
             a.step, a.fields, a.detail, a.notes, a.application_id))
        con.commit()
        print(f"OK stuck id={cur.lastrowid}")
    elif a.action in ("done", "dismiss"):
        if not a.id:
            fail(f"stuck {a.action} requires --id")
        _block_secret(a.resolution)  # a stuck-job resolution is where a typed document/password could land
        st = "done" if a.action == "done" else "dismissed"
        con.execute("UPDATE stuck_jobs SET status=?, resolution=COALESCE(?,resolution), resolved_at=datetime('now','localtime') WHERE id=?",
                    (st, a.resolution, a.id))
        con.commit()
        print(f"OK stuck id={a.id} {st}")
    else:
        cond, params = ["status=?"], [a.status or "open"]
        if a.kind:
            cond.append("kind=?"); params.append(a.kind)
        if a.routine:
            cond.append("routine=?"); params.append(a.routine)
        output(con.execute(
            f"SELECT id,date,kind,company,title,fit,step,fields,url,form_url,site,routine,detail FROM stuck_jobs WHERE {' AND '.join(cond)}"
            " ORDER BY COALESCE(fit,0) DESC, id", params), a.json)


def cmd_report(a):
    con = connect(read_only=True)
    d = a.date or today()
    apps = con.execute("SELECT company,title,status,url,source FROM applications WHERE date=? ORDER BY id", (d,)).fetchall()
    valid = [c for c in apps if c["status"] != "uncertain"]
    uncertain = [c for c in apps if c["status"] == "uncertain"]
    print(f"# Summary {d} — {len(valid)} applications\n")
    print(f"## Applications ({len(valid)})")
    for c in valid:
        print(f"- {c['company']} — {c['title']} — {c['status']} — {c['source'] or ''} — {c['url'] or 'no URL'}")
    if uncertain:
        print(f"\n## Uncertain — sent without confirmation, not counted ({len(uncertain)})")
        for c in uncertain:
            print(f"- {c['company']} — {c['title']} — {c['url'] or 'no URL'}")
    logs = con.execute("SELECT ts,kind,text FROM run_log WHERE run_date=? ORDER BY id", (d,)).fetchall()
    if logs:
        print("\n## Run log")
        for l in logs:
            print(f"- {l['ts'][11:16]} [{l['kind']}] {l['text']}")
    new_sites = con.execute("SELECT site,reason,detail FROM blocked_sites WHERE date=?", (d,)).fetchall()
    if new_sites:
        print("\n## Sites blocked today")
        for s in new_sites:
            print(f"- {s['site']} — {s['reason']} — {(s['detail'] or '')[:160]}")
    new_q = con.execute("SELECT question,agent_answer FROM questions WHERE date=?", (d,)).fetchall()
    if new_q:
        print("\n## New questions (please answer)")
        for p in new_q:
            print(f"- {p['question'][:200]} → agent answered: {(p['agent_answer'] or '')[:120]}")
    stuck = con.execute("SELECT id,date,kind,company,title,fit,step,fields,url,form_url FROM stuck_jobs WHERE status='open'"
                        " ORDER BY kind, COALESCE(fit,0) DESC, id").fetchall()
    if stuck:
        print(f"\n## Stuck jobs — you finish by hand ({len(stuck)} open)")
        kind = None
        for t in stuck:
            if t["kind"] != kind:
                kind = t["kind"]
                print(f"\n**{kind}**")
            fit = f" (fit {t['fit']})" if t["fit"] else ""
            where = f" — stopped at: {t['step']}" if t["step"] else ""
            missing = f" — missing: {t['fields']}" if t["fields"] else ""
            link = t["form_url"] or t["url"] or "no URL"
            print(f"- #{t['id']} {t['company'] or '?'} — {t['title'] or '?'}{fit}{where}{missing} — {link}")
    todos = con.execute("SELECT id,due,description,url FROM todos WHERE status='open' ORDER BY COALESCE(due,'9999'), id").fetchall()
    print(f"\n## Needs you ({len(todos)} open)")
    for p in todos:
        due = f"[due {p['due']}] " if p["due"] else ""
        print(f"- #{p['id']} {due}{p['description']}" + (f" — {p['url']}" if p["url"] else ""))


REPLIED = ("in-process", "interview", "offer", "test-pending", "rejected")
INTERVIEWED = ("interview", "offer")


def _funnel(rows, key):
    agg = {}
    for r in rows:
        k = key(r)
        d = agg.setdefault(k, {"n": 0, "resp": 0, "intv": 0})
        d["n"] += 1
        d["resp"] += r["status"] in REPLIED
        d["intv"] += r["status"] in INTERVIEWED
    return sorted(agg.items(), key=lambda kv: -kv[1]["n"])


def cmd_metrics(a):
    """Funnel and reply rate per source and per résumé variant — only aggregates what is already in the database."""
    con = connect(read_only=True)
    rows = con.execute("SELECT source,status,resume FROM applications WHERE status<>'uncertain'").fetchall()
    total = len(rows)
    resp_tot = sum(1 for r in rows if r["status"] in REPLIED)
    intv_tot = sum(1 for r in rows if r["status"] in INTERVIEWED)
    pct = lambda x, n: f"{(100 * x / n):.0f}%" if n else "—"
    by_source = _funnel(rows, lambda r: r["source"].split(" ")[0] if r["source"] else "(no source)")
    by_resume = _funnel(rows, lambda r: r["resume"] or "default")
    if a.json:
        conv = lambda items: [{"name": k, "applications": d["n"], "replies": d["resp"], "interviews": d["intv"]} for k, d in items]
        print(json.dumps({"total": total, "replies": resp_tot, "interviews": intv_tot,
                          "by_source": conv(by_source), "by_resume": conv(by_resume)}, ensure_ascii=False))
        return
    print(f"# Metrics — {total} applications (excludes uncertain)")
    print(f"Reply rate: {pct(resp_tot, total)} ({resp_tot}) | Interview rate: {pct(intv_tot, total)} ({intv_tot})\n")
    for label, items in (("source", by_source), ("resume", by_resume)):
        print(f"{label}\tapplications\treplies\treply_rate\tinterviews\tinterview_rate")
        for k, d in items:
            print(f"{k}\t{d['n']}\t{d['resp']}\t{pct(d['resp'], d['n'])}\t{d['intv']}\t{pct(d['intv'], d['n'])}")
        print()


def cmd_followups(a):
    """Applications applied/no-reply for >= N days (default 7) — follow-up candidates (the agent/you decide)."""
    con = connect(read_only=True)
    limit = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    rows = con.execute(
        "SELECT a.id,a.date,a.company,a.title,a.source,a.status,a.url,"
        " (SELECT MAX(d.date) FROM drafts d WHERE d.application_id=a.id AND d.kind='follow-up') AS last_draft"
        " FROM applications a WHERE a.status IN ('applied','no-reply') AND a.date<=? ORDER BY a.date, a.id", (limit,)).fetchall()
    output(rows, a.json)


def cmd_context(a):
    """Everything known about one application, as JSON — the grounding input for drafts and interview prep."""
    con = connect(read_only=True)
    r = con.execute("SELECT * FROM applications WHERE id=?", (a.id,)).fetchone()
    if not r:
        fail(f"application id={a.id} does not exist")
    comp = slug(r["company"])
    ctx = {
        "application": dict(r),
        # interactions tied to this application, or with anyone at the same company
        "contacts": [dict(x) for x in con.execute(
            "SELECT date,person,company,channel,direction,summary,application_id FROM contacts ORDER BY date").fetchall()
            if x["application_id"] == a.id or (x["company"] and slug(x["company"]) == comp)],
        "people": [dict(x) for x in con.execute("SELECT name,company,role,profile_url,notes FROM people").fetchall()
                   if x["company"] and slug(x["company"]) == comp],
        "todos": [dict(x) for x in con.execute("SELECT date,description,status FROM todos WHERE application_id=?", (a.id,))],
        "drafts": [dict(x) for x in con.execute("SELECT date,kind,path,status FROM drafts WHERE application_id=?", (a.id,))],
        "answered_questions": [dict(x) for x in con.execute(
            "SELECT question,official_answer FROM questions WHERE official_answer IS NOT NULL AND official_answer<>''")],
        "drafts_dir": config.DRAFTS,
    }
    print(json.dumps(ctx, ensure_ascii=False, indent=1))


def cmd_draft(a):
    con = connect()
    if a.action == "add":
        if a.kind not in DRAFT_KINDS:
            fail(f"invalid kind: {a.kind} (valid: {', '.join(DRAFT_KINDS)})")
        if not a.path or not os.path.exists(a.path):
            fail(f"draft file does not exist: {a.path}")
        company, title = a.company, a.title
        if a.application_id:
            r = con.execute("SELECT company,title FROM applications WHERE id=?", (a.application_id,)).fetchone()
            if not r:
                fail(f"application id={a.application_id} does not exist")
            company, title = company or r["company"], title or r["title"]
        cur = con.execute("INSERT INTO drafts (date,kind,application_id,company,title,path) VALUES (?,?,?,?,?,?)",
                          (today(), a.kind, a.application_id, company, title, os.path.abspath(a.path)))
        con.commit()
        print(f"OK draft id={cur.lastrowid}")
    elif a.action in ("sent", "archive"):
        if not a.id:
            fail(f"draft {a.action} requires --id")
        st = "sent" if a.action == "sent" else "archived"
        n = con.execute("UPDATE drafts SET status=?, updated_at=datetime('now','localtime') WHERE id=?", (st, a.id)).rowcount
        con.commit()
        print(f"OK draft id={a.id} {st}" if n else f"ERROR draft id={a.id} does not exist")
    else:
        cond, args = "", []
        if a.kind:
            cond, args = " WHERE kind=?", [a.kind]
        output(con.execute(f"SELECT id,date,kind,application_id,company,title,path,status FROM drafts{cond} ORDER BY id DESC", args), a.json)


def cmd_ghost_check(a):
    """Ghost-job score for one posting: GHOST=NN plus the signals behind it, and SKIP/OK against target.ghost_max."""
    import filters
    con = connect(read_only=True)
    text = ""
    if a.description_file:
        with open(a.description_file, encoding="utf-8") as f:
            text = f.read()
    times, span = seen_stats(con, a.company, a.title)
    score, signals = filters.ghost_score_detail(title=a.title, text=text, age_days=a.age_days,
                                                times_seen=times, seen_span_days=span)
    verdict = "SKIP" if score >= filters.GHOST_MAX else "OK"
    print(f"GHOST={score} MAX={filters.GHOST_MAX} {verdict}" + (" — " + "; ".join(signals) if signals else ""))


def cmd_pick_resume(a):
    """Which résumé to attach for this job (variants in config.resume_variants)."""
    text = ""
    if a.description_file:
        with open(a.description_file, encoding="utf-8") as f:
            text = f.read()
    p, name, hits = config.resume_for(a.title, text)
    print(f"RESUME={p}\nVARIANT={name}\nHITS={hits}" + ("" if os.path.exists(p) else "\nWARNING:file-missing"))


def cmd_sql(a):
    con = connect(read_only=True)
    try:
        show(con.execute(a.query))
    except sqlite3.Error as e:
        fail(f"{e}")


def cmd_export(a):
    con = connect(read_only=True)
    folder = config.VIEWS
    os.makedirs(folder, exist_ok=True)
    if getattr(a, "csv", False):
        import csv
        dest = os.path.join(folder, "applications.csv")
        cols = ("id", "date", "company", "title", "source", "status", "fit", "resume", "url", "notes")
        rows = con.execute(f"SELECT {','.join(cols)} FROM applications ORDER BY date DESC, id DESC").fetchall()
        with open(dest, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] for c in cols])
        print(f"OK {dest}")
        return
    views = {
        "applications.md": "SELECT date,company,title,source,status,fit,resume,url,notes FROM applications ORDER BY date DESC, id DESC",
        "todos.md": "SELECT id,date,due,description,url FROM todos WHERE status='open' ORDER BY COALESCE(due,'9999')",
        "stuck-jobs.md": "SELECT id,date,kind,company,title,fit,step,fields,url,form_url,site,routine,detail FROM stuck_jobs WHERE status='open' ORDER BY kind, COALESCE(fit,0) DESC",
        "questions.md": "SELECT id,status,question,agent_answer,official_answer FROM questions ORDER BY status, id",
        "blocked-sites.md": "SELECT id,date,site,reason,attempts,status,detail FROM blocked_sites ORDER BY status, site",
        "contacts.md": "SELECT name,company,role,profile_url,email,notes FROM people ORDER BY name",
    }
    for name, sql in views.items():
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(f"> Generated by `jobdb.py export` at {now()} — read-only; edit through jobdb.py.\n\n")
            f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
            for r in rows:
                f.write("| " + " | ".join("" if r[c] is None else str(r[c]).replace("|", "/").replace("\n", " ") for c in cols) + " |\n")
    print(f"OK {folder}")


# ---------- CLI ----------
def main():
    p = argparse.ArgumentParser(description="Aplica — the apply engine's database (SQLite)")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init", help="create the tables (idempotent)").set_defaults(f=cmd_init)
    sp.add_parser("check", help="health check: file, integrity and tables. Last line OK or ERROR:<reason>").set_defaults(f=cmd_check)
    sp.add_parser("backup", help=f"consistent copy in backups/ (keeps {KEEP_BACKUPS})").set_defaults(f=cmd_backup)

    s = sp.add_parser("dedup", help="NEW | DUPLICATE ... | DISCARDED-BEFORE ... | STUCK ... | LEGACY-SEEN ...")
    s.add_argument("--url"); s.add_argument("--company"); s.add_argument("--title")
    s.set_defaults(f=cmd_dedup)

    s = sp.add_parser("add-application", help="record an application (runs dedup first; exit 2 if duplicate)")
    s.add_argument("--company", required=True); s.add_argument("--title", required=True)
    s.add_argument("--source"); s.add_argument("--url"); s.add_argument("--date")
    s.add_argument("--status", default="applied"); s.add_argument("--fit", type=int); s.add_argument("--notes")
    s.add_argument("--resume", help="résumé variant name used (from pick-resume)")
    s.add_argument("--force", action="store_true", help="only for a genuinely different job flagged DUPLICATE; never for DISCARDED-BEFORE")
    s.add_argument("--force-reason", help="required with --force; becomes a to-do for you to review")
    s.set_defaults(f=cmd_add_application)

    s = sp.add_parser("update-application", help="change status and/or append a dated note")
    s.add_argument("--id", type=int); s.add_argument("--url"); s.add_argument("--status")
    s.add_argument("--notes-append"); s.add_argument("--fit", type=int)
    s.set_defaults(f=cmd_update_application)

    s = sp.add_parser("add-discard", help="job that passed dedup but failed the gate")
    s.add_argument("--company", required=True); s.add_argument("--title", default="")
    s.add_argument("--url"); s.add_argument("--source"); s.add_argument("--reason", required=True); s.add_argument("--date")
    s.set_defaults(f=cmd_add_discard)

    s = sp.add_parser("applications", help="list/search applications (--json for the app's pipeline)")
    s.add_argument("--date"); s.add_argument("--status"); s.add_argument("--search"); s.add_argument("--limit", default=50)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_applications)

    s = sp.add_parser("today", help="today's applications (APPLICATIONS_COUNTED excludes uncertain)")
    s.add_argument("--date"); s.set_defaults(f=cmd_today)

    s = sp.add_parser("add-question", help="question with no answer in your material (dedup by text)")
    s.add_argument("--question", required=True); s.add_argument("--field-type"); s.add_argument("--company")
    s.add_argument("--platform"); s.add_argument("--url"); s.add_argument("--agent-answer"); s.add_argument("--date")
    s.set_defaults(f=cmd_add_question)

    s = sp.add_parser("questions", help="list questions; --answered = the ones you already answered (use them now)")
    s.add_argument("--status"); s.add_argument("--answered", action="store_true"); s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_questions)

    s = sp.add_parser("answer-question", help="store the official answer")
    s.add_argument("--id", type=int, required=True); s.add_argument("--answer", required=True)
    s.set_defaults(f=cmd_answer_question)

    s = sp.add_parser("add-site", help="site that blocked signup/login (adds an attempt if already blocked)")
    s.add_argument("--site", required=True); s.add_argument("--reason", required=True)
    s.add_argument("--url"); s.add_argument("--attempting"); s.add_argument("--detail"); s.add_argument("--date")
    s.set_defaults(f=cmd_add_site)

    s = sp.add_parser("update-site", help="mark resolved/dismissed")
    s.add_argument("--id", type=int, required=True); s.add_argument("--status"); s.add_argument("--resolution")
    s.set_defaults(f=cmd_update_site)

    sp.add_parser("active-sites", help="blocked/dismissed sites + cooldown").set_defaults(f=cmd_active_sites)

    s = sp.add_parser("add-contact", help="interaction with a person (DM, connection, comment, email, call, meeting)")
    s.add_argument("--person", required=True); s.add_argument("--channel", required=True)
    s.add_argument("--direction", choices=("sent", "received"), required=True)
    s.add_argument("--company"); s.add_argument("--summary"); s.add_argument("--application-id", type=int); s.add_argument("--date")
    s.set_defaults(f=cmd_add_contact)

    s = sp.add_parser("person", help="CRM: create/update a person (company, role, profile URL, email, notes)")
    s.add_argument("--name", required=True); s.add_argument("--company"); s.add_argument("--role")
    s.add_argument("--profile-url"); s.add_argument("--email"); s.add_argument("--notes")
    s.set_defaults(f=cmd_person)

    s = sp.add_parser("contacts", help="CRM: people with last touch and counts")
    s.add_argument("--search"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_contacts)

    s = sp.add_parser("contact-history", help="CRM: every interaction with one person")
    s.add_argument("--person", required=True); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_contact_history)

    s = sp.add_parser("recent-contact", help="30-day rule: YES | POSSIBLE | NO (use --channel linkedin-dm for the DM rule)")
    s.add_argument("--person", required=True); s.add_argument("--days", type=int, default=30)
    s.add_argument("--channel", choices=CHANNELS, help="only count contacts on this channel (e.g. linkedin-dm)")
    s.set_defaults(f=cmd_recent_contact)

    x = sp.add_parser("interest-check", help="may we click \"I'm interested\" on the company's LinkedIn page? (per-company cooldown, daily cap, never the current employer)")
    x.add_argument("--company", required=True)
    x.set_defaults(f=cmd_interest_check)
    x = sp.add_parser("interest-pending", help="companies with a high-fit/in-process application still without \"I'm interested\"")
    x.add_argument("--days", type=int, default=7)
    x.add_argument("--min-fit", type=int, default=90)
    x.add_argument("--limit", type=int, default=3)
    x.set_defaults(f=cmd_interest_pending)

    x = sp.add_parser("add-post", help="add a post to the queue (status draft — you approve)")
    x.add_argument("--topic", required=True); x.add_argument("--hook"); x.add_argument("--file"); x.add_argument("--text")
    x.add_argument("--image"); x.add_argument("--position", type=int, default=100); x.add_argument("--notes")
    x.set_defaults(f=cmd_add_post)
    x = sp.add_parser("posts", help="list the post queue"); x.add_argument("--status"); x.set_defaults(f=cmd_posts)
    x = sp.add_parser("post-show", help="print a post's text"); x.add_argument("--id", type=int, required=True); x.set_defaults(f=cmd_post_show)
    x = sp.add_parser("post-status", help="approve/dismiss/back to draft")
    x.add_argument("--id", type=int, required=True); x.add_argument("--status", required=True, choices=["draft", "approved", "dismissed"]); x.add_argument("--notes")
    x.set_defaults(f=cmd_post_status)
    x = sp.add_parser("post-edit", help="replace the text (back to draft)")
    x.add_argument("--id", type=int, required=True); x.add_argument("--file"); x.add_argument("--text"); x.set_defaults(f=cmd_post_edit)
    x = sp.add_parser("post-next", help="routine: approved post to publish today? (interval caps.post_interval_days)"); x.set_defaults(f=cmd_post_next)
    x = sp.add_parser("post-published", help="mark a post as published")
    x.add_argument("--id", type=int, required=True); x.add_argument("--url"); x.set_defaults(f=cmd_post_published)

    sp.add_parser("social-today", help="LinkedIn social actions sent today (all routines) vs cap (caps.social_per_day)").set_defaults(f=cmd_social_today)
    sp.add_parser("linkedin-status", help="OK | BLOCKED (linkedin-block not yet resolved by you)").set_defaults(f=cmd_linkedin_status)

    s = sp.add_parser("lock", help="browser lock: acquire (exit 3 = BUSY) | wait (blocks up to --minutes and acquires; exit 3 = still busy) | release | check (subagent: exit 4 = STOP)")
    s.add_argument("action", choices=("acquire", "wait", "release", "check"))
    s.add_argument("--minutes", type=float, default=9, help="wait: max time for this call (≤9 to fit the tool's 10-min limit)"); s.add_argument("--owner", required=True)
    s.add_argument("--ttl-min", type=int, default=150, help="a lock older than this is considered abandoned")
    s.set_defaults(f=cmd_lock)

    s = sp.add_parser("control", help="key/value control block: show | get KEY | set KEY=value ... (empty value deletes)")
    s.add_argument("action", choices=("show", "get", "set")); s.add_argument("pairs", nargs="*")
    s.set_defaults(f=cmd_control)

    s = sp.add_parser("log", help="audit line for the run (batch, monitor, processes, notes)")
    s.add_argument("--kind", required=True); s.add_argument("--text", required=True); s.add_argument("--run-date")
    s.set_defaults(f=cmd_log)

    s = sp.add_parser("logs", help="a run's log"); s.add_argument("--date"); s.set_defaults(f=cmd_logs)

    s = sp.add_parser("todo", help="Needs you: list | add | done | dismiss")
    s.add_argument("action", choices=("list", "add", "done", "dismiss"))
    s.add_argument("--id", type=int); s.add_argument("--description"); s.add_argument("--due")
    s.add_argument("--url"); s.add_argument("--application-id", type=int); s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_todo)

    s = sp.add_parser("stuck", help="job the agent could not finish (document, password, new account, judgment...) — add | list | done | dismiss")
    s.add_argument("action", choices=("list", "add", "done", "dismiss"))
    s.add_argument("--id", type=int); s.add_argument("--kind", help=" | ".join(STUCK_KINDS))
    s.add_argument("--company"); s.add_argument("--title"); s.add_argument("--url", help="job link")
    s.add_argument("--form-url", help="link to the page/form where it stopped")
    s.add_argument("--site", help="platform (Gupy, Greenhouse, company site...)")
    s.add_argument("--routine", help="add: who recorded it (ats, linkedin-jobs...) · list: filter by it")
    s.add_argument("--fit", type=int); s.add_argument("--step", help="where it stopped (e.g. 'step 3/4 — personal data')")
    s.add_argument("--fields", help="missing fields, described — NEVER the value (e.g. 'national ID, account password')")
    s.add_argument("--detail", help="the site's literal message / why it got stuck"); s.add_argument("--notes", help="what was already filled, tips for you")
    s.add_argument("--application-id", type=int); s.add_argument("--date")
    s.add_argument("--status", help="list: open (default) | done | dismissed"); s.add_argument("--resolution")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_stuck)

    s = sp.add_parser("report", help="day summary in markdown (email body)")
    s.add_argument("--date"); s.set_defaults(f=cmd_report)

    s = sp.add_parser("metrics", help="funnel and reply/interview rate per source and per résumé variant (read-only)")
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_metrics)

    s = sp.add_parser("followups", help="applications applied/no-reply for >= N days (follow-up candidates)")
    s.add_argument("--days", type=int, default=7); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_followups)

    s = sp.add_parser("context", help="everything known about one application, as JSON (grounding for drafts/prep)")
    s.add_argument("--id", type=int, required=True); s.set_defaults(f=cmd_context)

    s = sp.add_parser("draft", help="grounded drafts (cover letter, follow-up, interview prep): list | add | sent | archive")
    s.add_argument("action", choices=("list", "add", "sent", "archive"))
    s.add_argument("--id", type=int); s.add_argument("--kind", help=" | ".join(DRAFT_KINDS)); s.add_argument("--application-id", type=int)
    s.add_argument("--company"); s.add_argument("--title"); s.add_argument("--path"); s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_draft)

    s = sp.add_parser("ghost-check", help="ghost-job score for a posting: GHOST=NN MAX=NN OK|SKIP — signals")
    s.add_argument("--company", required=True); s.add_argument("--title", required=True)
    s.add_argument("--age-days", type=int); s.add_argument("--description-file")
    s.set_defaults(f=cmd_ghost_check)

    s = sp.add_parser("pick-resume", help="which résumé variant to attach for a job (config.resume_variants)")
    s.add_argument("--title", required=True); s.add_argument("--description-file")
    s.set_defaults(f=cmd_pick_resume)

    s = sp.add_parser("sql", help="READ-ONLY query"); s.add_argument("query"); s.set_defaults(f=cmd_sql)
    s = sp.add_parser("export", help="write readable views/*.md (read-only); --csv writes applications.csv")
    s.add_argument("--csv", action="store_true"); s.set_defaults(f=cmd_export)

    a = p.parse_args()
    if a.cmd == "todo" and a.action == "add" and not a.description:
        p.error("todo add requires --description")
    if a.cmd == "stuck" and a.action == "add" and not (a.kind and (a.url or a.form_url)):
        p.error("stuck add requires --kind and --url (or --form-url)")
    if a.cmd == "todo" and a.action in ("done", "dismiss") and not a.id:
        p.error(f"todo {a.action} requires --id")
    if a.cmd == "draft" and a.action == "add" and not (a.kind and a.path):
        p.error("draft add requires --kind and --path")
    if a.cmd == "control" and a.action == "get" and len(a.pairs) != 1:
        p.error("control get requires 1 key")
    a.f(a)


if __name__ == "__main__":
    main()
