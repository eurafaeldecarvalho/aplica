#!/usr/bin/env python3
"""Config dir resolution and loading for Aplica — auto-apply for Claude Code.

A instância de cada usuário vive FORA do repositório, num diretório de config do
sistema operacional, para que nenhum dado pessoal ou credencial seja versionado:

  Linux/mac : $APLICA_HOME  |  $XDG_CONFIG_HOME/aplica  |  ~/.config/aplica
  Windows   : %APLICA_HOME% |  %APPDATA%\\aplica

Conteúdo do diretório (criado pelo app ou pelo setup-wizard):
  config.json   settings/toggles/alvo/fontes/agenda (schema: config.schema.json)
  profile.json  dados do candidato            (schema: profile.schema.json)
  answers.md    respostas abertas longas
  resume.pdf    currículo (anexado nas candidaturas)
  photo.jpg     foto do candidato
  state.db      estado (SQLite, via jobdb.py)
  backups/      cópias do state.db
  logs/ tmp/ visao/
"""
import json
import os

APP = "aplica"


def home():
    """Diretório de config do usuário. Cria se não existir."""
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


# Caminhos usados pelo motor (um banco por instância; override por env p/ testes).
DB = os.environ.get("APLICA_DB") or path("state.db")
BACKUPS = path("backups")
LOGS = path("logs")
TMP = path("tmp")
VISAO = path("visao")


# ---------- defaults (fazem o motor rodar mesmo com config parcial) ----------
# Defaults CONSERVADORES por padrão (produto público): ações sociais desligadas,
# tetos baixos. Cada usuário liga o que quiser no app / config.json.
DEFAULTS = {
    "schema_version": 1,
    "target": {
        # termos de busca (o agente usa ao pesquisar nos boards/LinkedIn)
        "titles_search": ["Software Engineer", "Backend Engineer", "Developer"],
        # regex de título aceito / barrado (knockout por cargo)
        "title_ok": r"engineer|developer|desenvolvedor|engenheir",
        "title_bad": r"junior|j[uú]nior|jr\b|intern|est[aá]gi|trainee",
        # stack-alvo e stacks fora (knockout por linguagem principal)
        "stack_target": r"",
        "stack_out": {},
        # geografia: listas de palavras; vazio em geo_allow = aceita qualquer local
        "geo_allow": ["remote", "remoto", "worldwide", "anywhere", "global"],
        "geo_block": [],
        # idioma de trabalho e bloqueio por idioma obrigatório
        "work_language": ["english", "portuguese"],
        "language_required_block": r"",
        # cidade do usuário (presencial/híbrido só vale aqui)
        "home_city": "",
        # modalidades aceitas
        "work_modes": {"remote": True, "hybrid": False, "onsite": False},
    },
    "behavior": {
        # feed do LinkedIn: full | apply_only | off  (OFF por padrão — maior risco de ban)
        "feed_mode": "off",
        "social": {"comment": False, "connect": False, "dm": False, "like": False},
        "im_interested": False,
        "email_resume": False,
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
    },
    "sources": {
        "ats": True, "linkedin_jobs": True, "remotive": True,
        "freehire": True, "linkedin_feed": False,
    },
    "current_employer": [],
    "paths": {"resume": "resume.pdf", "photo": "photo.jpg"},
}


def _deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


_CACHE = {}


def load_config():
    """config.json do usuário mesclado sobre os defaults. Cacheado por processo."""
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
    """profile.json do usuário (dados do candidato). {} se ainda não existir."""
    p = path("profile.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def resume_path():
    rel = load_config()["paths"].get("resume", "resume.pdf")
    return rel if os.path.isabs(rel) else path(rel)


def photo_path():
    rel = load_config()["paths"].get("photo", "photo.jpg")
    return rel if os.path.isabs(rel) else path(rel)


if __name__ == "__main__":
    # Diagnóstico: `python config.py` mostra os caminhos resolvidos.
    print("home   :", home())
    print("db     :", DB)
    print("config :", path("config.json"), "(existe)" if os.path.exists(path("config.json")) else "(ausente)")
    print("profile:", path("profile.json"), "(existe)" if os.path.exists(path("profile.json")) else "(ausente)")
