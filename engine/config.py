#!/usr/bin/env python3
"""Config dir resolution and loading for Aplica — auto-apply for Claude Code.

Each user's instance lives OUTSIDE the repository, in an OS config directory, so that no
personal data or credential is ever versioned:

  Linux/mac : $APLICA_HOME  |  $XDG_CONFIG_HOME/aplica  |  ~/.config/aplica
  Windows   : %APLICA_HOME% |  %APPDATA%\\aplica

Directory contents (created by the app or by the setup-wizard):
  config.json   settings/toggles/target/sources/schedule (schema: config.schema.json)
  profile.json  candidate data                           (schema: profile.schema.json)
  answers.md    long open-ended answers
  resume.pdf    résumé (attached to applications; variants in config.resume_variants)
  photo.jpg     candidate photo
  state.db      state (SQLite, via jobdb.py)
  backups/      state.db copies
  drafts/       grounded drafts (cover letters, follow-ups, interview prep)
  logs/ tmp/ views/
"""
import json
import os
import re

APP = "aplica"


def home():
    """User config directory. Created if missing."""
    env = os.environ.get("APLICA_HOME")
    if env:
        base = env
    elif os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(root, APP)
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        base = os.path.join(root, APP)
    os.makedirs(base, exist_ok=True)
    return base


def path(*parts):
    return os.path.join(home(), *parts)


# Paths used by the engine (one database per instance; env override for tests).
DB = os.environ.get("APLICA_DB") or path("state.db")
BACKUPS = path("backups")
LOGS = path("logs")
TMP = path("tmp")
VIEWS = path("views")
DRAFTS = path("drafts")


# ---------- defaults (let the engine run even with a partial config) ----------
# CONSERVATIVE by default (public product): social actions off, low caps.
# Each user turns on what they want in the app / config.json.
DEFAULTS = {
    "schema_version": 1,
    "target": {
        # search terms (the agent uses them when searching boards/LinkedIn)
        "titles_search": ["Software Engineer", "Backend Engineer", "Developer"],
        # accepted / blocked title regex (title knockout)
        "title_ok": r"engineer|developer|desenvolvedor|engenheir",
        "title_bad": r"junior|j[uú]nior|jr\b|intern|est[aá]gi|trainee",
        # target stack and out-of-scope stacks (main-language knockout)
        "stack_target": r"",
        "stack_out": {},
        # geography: word lists; empty geo_allow = accept any location
        "geo_allow": ["remote", "remoto", "worldwide", "anywhere", "global"],
        "geo_block": [],
        # companies/recruiters to never apply to (name knockout)
        "company_block": [],
        # working language and required-language block
        "work_language": ["english", "portuguese"],
        "language_required_block": r"",
        # user's city (on-site/hybrid only counts here)
        "home_city": "",
        # accepted work modes
        "work_modes": {"remote": True, "hybrid": False, "onsite": False},
        # ghost-job score (0-100) at or above which a posting is skipped
        "ghost_max": 60,
    },
    "behavior": {
        # LinkedIn feed: full | apply_only | off  (OFF by default — highest ban risk)
        "feed_mode": "off",
        "social": {"comment": False, "connect": False, "dm": False, "like": False},
        "im_interested": False,
        "email_resume": False,
        "email_summary": False,
        "sso_google": True,
        "create_account": False,
    },
    "caps": {
        "applications_per_day": 15,
        "max_batches": 10,
        "batch_size": 5,
        "social_per_day": 0,
        "interest_per_day": 0,
        "interest_cooldown_days": 180,
        "post_interval_days": 7,
        "cadence_seconds": [45, 240],
        # human-hours window (empty = no restriction); the agent avoids acting outside it
        "active_hours": {"start": "", "end": ""},
    },
    "sources": {
        "ats": True, "linkedin_jobs": True,
        "freehire": True, "linkedin_feed": False,
    },
    "current_employer": [],
    "paths": {"resume": "resume.pdf", "photo": "photo.jpg"},
    # résumé variants: [{"name", "file", "keywords"}] — keywords is a regex matched against the
    # job title + description; the variant with the most hits wins, else paths.resume.
    "resume_variants": [],
    # desktop-app-only settings (the engine ignores them)
    "app": {"desktop_notifications": True},
}


def _deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if v is None:
            # null in the user's config never overrides a default (keeps the conservative value).
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


_CACHE = {}


def load_config():
    """User config.json merged over the defaults. Cached per process."""
    if "config" in _CACHE:
        return _CACHE["config"]
    cfg = DEFAULTS
    p = path("config.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg = _deep_merge(DEFAULTS, json.load(f))
    _CACHE["config"] = cfg
    return cfg


def load_profile():
    """User profile.json (candidate data). {} if it does not exist yet."""
    p = path("profile.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _abs(rel):
    return rel if os.path.isabs(rel) else path(rel)


def resume_path():
    return _abs(load_config()["paths"].get("resume", "resume.pdf"))


def photo_path():
    return _abs(load_config()["paths"].get("photo", "photo.jpg"))


def resume_for(title, text=""):
    """(absolute path, variant name, hits) of the best résumé for a job.

    Scores each configured variant by how many times its `keywords` regex matches the title
    (weighted x3) and description. No variant with a hit → the default résumé (paths.resume).
    A variant whose file is missing is skipped, so a run never attaches a non-existent file.
    """
    best = (resume_path(), "default", 0)
    for v in load_config().get("resume_variants") or []:
        kw, f = (v or {}).get("keywords") or "", (v or {}).get("file") or ""
        if not kw or not f or not os.path.exists(_abs(f)):
            continue
        try:
            rx = re.compile(kw, re.I)
        except re.error:
            continue
        hits = 3 * len(rx.findall(title or "")) + len(rx.findall(text or ""))
        if hits > best[2]:
            best = (_abs(f), v.get("name") or os.path.basename(f), hits)
    return best


if __name__ == "__main__":
    # Diagnostics: `python config.py` prints the resolved paths.
    print("home   :", home())
    print("db     :", DB)
    print("config :", path("config.json"), "(exists)" if os.path.exists(path("config.json")) else "(missing)")
    print("profile:", path("profile.json"), "(exists)" if os.path.exists(path("profile.json")) else "(missing)")
