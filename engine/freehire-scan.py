#!/usr/bin/env python3
# Aplica — busca vagas no agregador freehire.me (API pública JSON, ~50 ATS), aplica dedup +
# knockouts do config e devolve as que valem abrir. Mesma saída dos outros scans.
#
# Uso: python freehire-scan.py [--dias 3] [--paginas 3] [--min-fit 70]
# Saída: FH|empresa|título|local|url|fit=NN  + linha de resumo.
# Exit 0 = ok · 4 = API indisponível (a rotina só pula esta fonte).
#
# Termos de busca e skills-alvo saem do config (target.titles_search / target.stack_target).
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
import filtros, jobdb
import config

BASE = os.environ.get("FREEHIRE_API_URL", "https://freehire.me")
_T = config.load_config().get("target") or {}
# termos de busca: primeiras palavras dos títulos-alvo, minúsculas, deduplicadas
BUSCAS = _T.get("freehire_queries") or [s.split()[-1].lower() for s in (_T.get("titles_search") or ["developer"]) if s.split()][:4] or ["developer"]
# skills-alvo: extrai palavras alfanuméricas do regex stack_target do config
ALVO_SKILLS = {w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9.]+", _T.get("stack_target") or "") if len(w) > 1}
IDIOMAS_OK = {l[:2].lower() for l in (_T.get("work_language") or ["english", "portuguese"])} | {None, ""}
_LANG_CODE = {"english": "en", "portuguese": "pt", "ingles": "en", "portugues": "pt", "spanish": "es"}
IDIOMAS_OK |= {_LANG_CODE.get(l.lower(), l[:2].lower()) for l in (_T.get("work_language") or [])}


def busca(params):
    url = f"{BASE}/api/v1/agent/jobs/search?" + urllib.parse.urlencode(params, doseq=True)
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "aplica/1.0"}), timeout=30) as r:
                try:
                    return json.load(r)
                except ValueError as e:
                    # resposta não-JSON (HTML de WAF/erro com status 200) → fonte indisponível, não crash
                    raise ConnectionError(f"freehire respondeu não-JSON: {e}") from e
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(5 * (tentativa + 1))
                continue
            # 4xx (403/404/etc.) não é recuperável → trata como fonte indisponível (exit 4), não exit 1
            raise ConnectionError(f"freehire HTTP {e.code}: {url[:120]}") from e
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (tentativa + 1))
    raise ConnectionError(f"freehire indisponível: {url[:120]}")


def texto_limpo(s):
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def avaliar(j):
    """(passa, motivo) para uma vaga do freehire, antes do dedup."""
    titulo, local = j.get("title") or "", j.get("location") or ""
    if not filtros.titulo_passa(titulo):
        return False, "título"
    if not filtros.empresa_passa(j.get("company") or ""):
        return False, "empresa-bloqueada"
    if not filtros.local_passa(local):
        return False, "local"
    enr = j.get("enrichment") or {}
    if IDIOMAS_OK and enr.get("posting_language") not in IDIOMAS_OK:
        return False, "idioma"
    if (j.get("reality") or {}).get("fake_freshness"):
        return False, "falsa novidade"
    skills = {s.lower() for s in (j.get("skills") or [])}
    if ALVO_SKILLS and skills and not skills & ALVO_SKILLS:
        return False, "stack"
    motivo = filtros.knockout_descricao(texto_limpo(j.get("description")), local)
    if motivo:
        return False, "descrição"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=3)
    ap.add_argument("--paginas", type=int, default=3, help="páginas de 50 por busca")
    ap.add_argument("--min-fit", type=int, default=70)
    a = ap.parse_args()

    con = jobdb.conectar(somente_leitura=True)
    vistas = jobdb.urls_vistas(con)
    vistos, aprovadas, cont, total = set(), [], {}, 0
    try:
        for q in BUSCAS:
            for pag in range(a.paginas):
                d = busca({"q": q, "limit": 50, "offset": pag * 50, "posted_within_days": a.dias,
                           "work_mode": "remote", "description_format": "text"})
                itens = d.get("data") or []
                total += len(itens)
                for j in itens:
                    url = j.get("url") or ""
                    if url in vistos:
                        continue
                    vistos.add(url)
                    ok, motivo = avaliar(j)
                    if not ok:
                        cont[motivo] = cont.get(motivo, 0) + 1
                        continue
                    if jobdb.norm_url(url) in vistas or jobdb.dedup(con, url, j.get("company"), j.get("title")) != "NOVA":
                        cont["já vista"] = cont.get("já vista", 0) + 1
                        continue
                    idade = (j.get("reality") or {}).get("age_days")
                    loc = j.get("location") or "/".join(j.get("regions") or [])
                    fit = filtros.nota_fit(j.get("title"), loc + " " + " ".join(j.get("regions") or []), idade,
                                           texto_limpo(j.get("description")))
                    aprovadas.append((fit, j, loc))
                if len(itens) < 50:
                    break
    except ConnectionError as e:
        if not total:
            print(f"FONTE_INDISPONIVEL: {e}")
            sys.exit(4)
        cont["erro parcial"] = 1

    aprovadas.sort(key=lambda t: -t[0])
    mostradas = [t for t in aprovadas if t[0] >= a.min_fit]
    for fit, j, loc in mostradas:
        print(f"FH|{j.get('company')}|{j.get('title')}|{loc}|{j.get('url')}|fit={fit}"[:300])
    print(f"# freehire: {total} resultados ({len(vistos)} únicos) | cortadas: "
          + ", ".join(f"{k} {v}" for k, v in sorted(cont.items())) + f" | para aplicar (fit>={a.min_fit}): {len(mostradas)}")


if __name__ == "__main__":
    main()
