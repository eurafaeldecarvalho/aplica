"""Aplica — knockout filters, fit score and ghost-job score shared by the scanners (ats, linkedin, freehire).

100% config-driven: the knockouts (title, stack, geography, language, work mode) are built from the
`target` block of the user's config.json. NO fixed profile here — with an empty config the filters
are permissive (almost everything passes) and the fit score falls back to a baseline.
Mirrors the knockouts of the apply-engine skill; if those change, adjust the config, not this file.

The keyword patterns below match both English and Portuguese postings on purpose: they read job
text, which comes in the posting's language.
"""
import re
import sys
import config

_T = config.load_config().get("target") or {}


def _rx(pattern, field="regex"):
    """Compile a case-insensitive regex, or None if empty. An invalid regex is NOT swallowed silently
    (that would turn a safety knockout off): warn on stderr and treat it as absent."""
    if not pattern:
        return None
    try:
        return re.compile(pattern, re.I)
    except re.error as e:
        print(f"[aplica] WARNING: invalid regex in target.{field} ({e}); that filter is OFF. Fix the config.", file=sys.stderr)
        return None


def _rx_words(words):
    """Compile a word list into a regex alternation, or None if empty."""
    words = [w for w in (words or []) if w]
    if not words:
        return None
    return re.compile("|".join(re.escape(w) for w in words), re.I)


# --- title ---
TITLE_OK = _rx(_T.get("title_ok"), "title_ok")
TITLE_BAD = _rx(_T.get("title_bad"), "title_bad")

# --- stack ---
STACK_TARGET = _rx(_T.get("stack_target"), "stack_target")
STACK_OUT = {k: r for k, r in ((k, _rx(v, f"stack_out.{k}")) for k, v in (_T.get("stack_out") or {}).items()) if r}

# --- geography ---
GEO_OK = _rx_words(_T.get("geo_allow"))
GEO_BAD = _rx_words(_T.get("geo_block"))

# --- blocked companies/recruiters (user blocklist) ---
COMPANY_BLOCK = _rx_words(_T.get("company_block"))

# --- language ---
LANGUAGE_BLOCK = _rx(_T.get("language_required_block"), "language_required_block")

# --- work mode ---
HOME_CITY = (_T.get("home_city") or "").strip().lower()
WORK_MODES = _T.get("work_modes") or {"remote": True, "hybrid": False, "onsite": False}

ONSITE = re.compile(r"presencial|h[ií]brid|hybrid|on-?site|in-office|escrit[oó]rio|\bdias? na (sede|empresa)", re.I)
REMOTE = re.compile(r"remot|work from home|home.?office|fully distributed|anywhere", re.I)
CYRILLIC = re.compile(r"[Ѐ-ӿ]")

# worldwide/americas for the fit score (independent of the config — fixed geographic concepts)
GEO_WORLD = re.compile(r"worldwide|anywhere|global", re.I)
GEO_AMERICAS = re.compile(r"latam|latin|americas|brazil|brasil|south america", re.I)
SENIOR = re.compile(r"senior|sênior|sr\.?\b|staff|lead|principal|especialista", re.I)
MID = re.compile(r"\bmid\b|intermediate|pleno", re.I)


def title_ok(title):
    t = title or ""
    if TITLE_OK and not TITLE_OK.search(t):
        return False
    if TITLE_BAD and TITLE_BAD.search(t):
        return False
    return True


def company_ok(company):
    """False if the company/recruiter is on the user's blocklist (target.company_block)."""
    if COMPANY_BLOCK and COMPANY_BLOCK.search(company or ""):
        return False
    return True


def location_ok(location):
    loc = location or ""
    if CYRILLIC.search(loc):
        return False
    if GEO_BAD and GEO_BAD.search(loc):
        return False
    # With an allowlist, the location must match it OR be remote (remote is accepted by default).
    if GEO_OK and not GEO_OK.search(loc) and not REMOTE.search(loc):
        return False
    return True


def description_knockout(text, location=""):
    """Knockout reason read from the description, or None."""
    t = text or ""
    loc = (location or "").lower()
    # work mode
    if ONSITE.search(t) and not REMOTE.search(t):
        accepts_onsite = WORK_MODES.get("onsite") or WORK_MODES.get("hybrid")
        in_city = HOME_CITY and HOME_CITY in loc
        if not (accepts_onsite and in_city):
            return "work mode: on-site/hybrid outside your city"
    # geography (description)
    if GEO_BAD and GEO_BAD.search(t) and not (GEO_OK and GEO_OK.search(t)):
        return "geography: market outside the target (description)"
    # required language
    if LANGUAGE_BLOCK and LANGUAGE_BLOCK.search(t):
        return "language: required language outside the target"
    # main stack
    if STACK_OUT:
        target = len(STACK_TARGET.findall(t)) if STACK_TARGET else 0
        out = {k: len(r.findall(t)) for k, r in STACK_OUT.items()}
        worst, n = max(out.items(), key=lambda kv: kv[1])
        if target == 0 and n >= 2:
            return f"stack: {worst} without the target stack"
        if n >= 4 and n > 2 * target:
            return f"stack: {worst} as the main language"
    return None


def fit_score_detail(title, location, age_days=None, text=""):
    """(score 0–100, [reasons]) — why the score is what it is (no black box)."""
    t, l = title or "", location or ""
    s, reasons = 0, []
    if STACK_TARGET and STACK_TARGET.search(t):
        s += 45; reasons.append("+45 target stack in title")
    elif TITLE_OK and TITLE_OK.search(t):
        s += 35; reasons.append("+35 matching title")
    else:
        s += 30; reasons.append("+30 baseline (no profile configured)")
    if text and STACK_TARGET and STACK_TARGET.search(text) and not STACK_TARGET.search(t):
        s += 5; reasons.append("+5 target stack in description")
    if GEO_WORLD.search(l):
        s += 30; reasons.append("+30 worldwide/global")
    elif GEO_AMERICAS.search(l) or (GEO_OK and GEO_OK.search(l)):
        s += 25; reasons.append("+25 target market")
    elif re.search(r"remote|remoto", l, re.I):
        s += 15; reasons.append("+15 remote")
    if SENIOR.search(t) or MID.search(t):
        s += 10; reasons.append("+10 seniority")
    else:
        s += 5
    if age_days is None:
        s += 8
    elif age_days <= 14:
        s += 15; reasons.append("+15 recent posting (<14d)")
    elif age_days <= 30:
        s += 8
    return min(s, 100), reasons


def fit_score(title, location, age_days=None, text=""):
    """Score 0–100 (same scale across all scanners)."""
    return fit_score_detail(title, location, age_days, text)[0]


# ---------- ghost jobs ----------
# A "ghost job" is a posting with no real, current opening behind it: evergreen talent pools,
# postings left up for months, or the same role re-posted over and over. Applying to them wastes
# the daily cap. The score is a transparent sum of signals; nothing is hidden.
GHOST_MAX = int(_T.get("ghost_max") or 60)
EVERGREEN = re.compile(
    r"talent (pool|community|network)|future (opportunit|opening|role)|always (looking|hiring)|general application|"
    r"evergreen|pipeline (role|requisition)|join our (talent|network)|no (current|specific) opening|"
    r"banco de talentos|oportunidades futuras|cadastro reserva", re.I)


def ghost_score_detail(title="", text="", age_days=None, times_seen=1, seen_span_days=0, fake_freshness=False):
    """(score 0–100, [signals]). `times_seen`/`seen_span_days` come from the seen_postings table
    (how often and over how long the same company+title was seen by the scanners)."""
    s, signals = 0, []
    if fake_freshness:
        s += 40; signals.append("+40 re-dated posting (source flags fake freshness)")
    if age_days is not None:
        if age_days > 60:
            s += 40; signals.append(f"+40 open {age_days} days")
        elif age_days > 30:
            s += 20; signals.append(f"+20 open {age_days} days")
    if times_seen >= 3 and seen_span_days >= 21:
        s += 30; signals.append(f"+30 re-posted {times_seen}x over {seen_span_days} days")
    elif times_seen >= 2 and seen_span_days >= 45:
        s += 20; signals.append(f"+20 seen again after {seen_span_days} days")
    if EVERGREEN.search(f"{title} {text or ''}"):
        s += 35; signals.append("+35 evergreen/talent-pool wording")
    if text and len(text) < 400:
        s += 10; signals.append("+10 very short description")
    return min(s, 100), signals


def ghost_score(**kw):
    return ghost_score_detail(**kw)[0]
