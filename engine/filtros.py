"""Aplica — filtros e nota de fit compartilhados pelos scans (ats, linkedin, remotive, freehire).

100% config-driven: os knockouts (título, stack, geografia, idioma, modalidade) são montados a
partir do bloco `target` do config.json do usuário. NADA de perfil fixo aqui — se o config vier
vazio, os filtros ficam permissivos (passa quase tudo) e a nota de fit cai para um baseline.
Espelha os knockouts do skill apply-engine; mudou lá, ajuste o config, não este arquivo.
"""
import re
import config

_T = config.load_config().get("target", {})


def _rx(pattern):
    """Compila um regex (case-insensitive) ou devolve None se o pattern estiver vazio."""
    if not pattern:
        return None
    try:
        return re.compile(pattern, re.I)
    except re.error:
        return None


def _rx_words(words):
    """Compila uma lista de palavras numa alternância regex, ou None se vazia."""
    words = [w for w in (words or []) if w]
    if not words:
        return None
    return re.compile("|".join(re.escape(w) for w in words), re.I)


# --- título ---
TITULO_OK = _rx(_T.get("title_ok"))
TITULO_RUIM = _rx(_T.get("title_bad"))

# --- stack ---
STACK_ALVO = _rx(_T.get("stack_target"))
STACK_FORA = {k: _rx(v) for k, v in (_T.get("stack_out") or {}).items() if _rx(v)}

# --- geografia ---
LOCAL_OK = _rx_words(_T.get("geo_allow"))
LOCAL_RUIM = _rx_words(_T.get("geo_block"))

# --- empresas/recrutadores barrados (blocklist do usuário) ---
COMPANY_BLOCK = _rx_words(_T.get("company_block"))

# --- idioma ---
LINGUA_BLOQUEIO = _rx(_T.get("language_required_block"))

# --- modalidade ---
HOME_CITY = (_T.get("home_city") or "").strip().lower()
WORK_MODES = _T.get("work_modes") or {"remote": True, "hybrid": False, "onsite": False}

PRESENCIAL = re.compile(r"presencial|h[ií]brid|hybrid|on-?site|in-office|escrit[oó]rio|\bdias? na (sede|empresa)", re.I)
REMOTO = re.compile(r"remot|work from home|home.?office|fully distributed|anywhere", re.I)
CIRILICO = re.compile(r"[Ѐ-ӿ]")

# worldwide/americas para a nota de fit (independe do config — são conceitos geográficos fixos)
GEO_MUNDO = re.compile(r"worldwide|anywhere|global", re.I)
GEO_AMERICAS = re.compile(r"latam|latin|americas|brazil|brasil|south america", re.I)
SENIOR = re.compile(r"senior|sênior|sr\.?\b|staff|lead|principal|especialista", re.I)
PLENO = re.compile(r"\bmid\b|intermediate|pleno", re.I)


def titulo_passa(titulo):
    t = titulo or ""
    if TITULO_OK and not TITULO_OK.search(t):
        return False
    if TITULO_RUIM and TITULO_RUIM.search(t):
        return False
    return True


def empresa_passa(empresa):
    """False se a empresa/recrutador está na blocklist do usuário (target.company_block)."""
    if COMPANY_BLOCK and COMPANY_BLOCK.search(empresa or ""):
        return False
    return True


def local_passa(local):
    local = local or ""
    if CIRILICO.search(local):
        return False
    if LOCAL_RUIM and LOCAL_RUIM.search(local):
        return False
    # Se há allowlist, o local precisa casar com ela OU ser remoto (remoto é aceito por padrão).
    if LOCAL_OK and not LOCAL_OK.search(local) and not REMOTO.search(local):
        return False
    return True


def knockout_descricao(texto, local=""):
    """Devolve o motivo do knockout lendo a descrição, ou None."""
    t = texto or ""
    loc = (local or "").lower()
    # modalidade
    presencial = PRESENCIAL.search(t) and not REMOTO.search(t)
    if presencial:
        aceita_presencial = WORK_MODES.get("onsite") or WORK_MODES.get("hybrid")
        na_cidade = HOME_CITY and HOME_CITY in loc
        if not (aceita_presencial and na_cidade):
            return "modalidade: presencial/híbrida fora da sua cidade"
    # geografia (descrição)
    if LOCAL_RUIM and LOCAL_RUIM.search(t) and not (LOCAL_OK and LOCAL_OK.search(t)):
        return "geografia: mercado fora do alvo (descrição)"
    # idioma obrigatório
    if LINGUA_BLOQUEIO and LINGUA_BLOQUEIO.search(t):
        return "idioma: idioma obrigatório fora do alvo"
    # stack principal
    if STACK_FORA:
        alvo = len(STACK_ALVO.findall(t)) if STACK_ALVO else 0
        fora = {k: len(r.findall(t)) for k, r in STACK_FORA.items()}
        if fora:
            pior, n = max(fora.items(), key=lambda kv: kv[1])
            if alvo == 0 and n >= 2:
                return f"stack: {pior} sem a stack-alvo"
            if n >= 4 and n > 2 * alvo:
                return f"stack: {pior} como linguagem principal"
    return None


def nota_fit_detalhe(titulo, local, idade_dias=None, texto=""):
    """(nota 0–100, [motivos]) — o porquê da nota, para transparência (nada de caixa-preta)."""
    t, l = titulo or "", local or ""
    s, reasons = 0, []
    if STACK_ALVO and STACK_ALVO.search(t):
        s += 45; reasons.append("+45 stack-alvo no título")
    elif TITULO_OK and TITULO_OK.search(t):
        s += 35; reasons.append("+35 título compatível")
    else:
        s += 30; reasons.append("+30 baseline (sem perfil configurado)")
    if texto and STACK_ALVO and STACK_ALVO.search(texto) and not STACK_ALVO.search(t):
        s += 5; reasons.append("+5 stack-alvo na descrição")
    if GEO_MUNDO.search(l):
        s += 30; reasons.append("+30 worldwide/global")
    elif GEO_AMERICAS.search(l) or (LOCAL_OK and LOCAL_OK.search(l)):
        s += 25; reasons.append("+25 mercado-alvo")
    elif re.search(r"remote|remoto", l, re.I):
        s += 15; reasons.append("+15 remoto")
    if SENIOR.search(t) or PLENO.search(t):
        s += 10; reasons.append("+10 senioridade")
    else:
        s += 5
    if idade_dias is None:
        s += 8
    elif idade_dias <= 14:
        s += 15; reasons.append("+15 vaga recente (<14d)")
    elif idade_dias <= 30:
        s += 8
    return min(s, 100), reasons


def nota_fit(titulo, local, idade_dias=None, texto=""):
    """Nota 0–100 (mesma escala do ats-scan)."""
    return nota_fit_detalhe(titulo, local, idade_dias, texto)[0]
