#!/usr/bin/env python3
# Aplica — busca vagas no LinkedIn pela API pública jobs-guest (SEM login, não usa a conta do
# usuário), lê a descrição de cada candidata, aplica dedup + knockouts do config e devolve só o
# que vale abrir no navegador.
#
# Uso: python linkedin-scan.py [--dias 1] [--paginas 2] [--max-detalhes 25] [--min-fit 70]
# Saída: LI|empresa|título|local|url|fit=NN  + linha final de resumo.
# Exit 0 = ok (lista pode estar vazia) · 3 = FALLBACK_NAVEGADOR (API não devolveu nada)
#
# Termos de busca (BUSCAS) = target.titles_search do config. Locais (LOCAIS) = target.linkedin_locations
# do config (default: sem restrição + remoto). Limite por IP apertado: ~7s+ entre chamadas.
import argparse, html, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request
import filtros, jobdb
import config

BASE = os.environ.get("LI_GUEST_BASE", "https://www.linkedin.com/jobs-guest/jobs/api")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8"}
PAUSA = (float(os.environ.get("LI_PAUSA_MIN", 9)), float(os.environ.get("LI_PAUSA_MAX", 13)))
ESPERA_429 = float(os.environ.get("LI_ESPERA_429", 60))

_T = config.load_config().get("target", {})
BUSCAS = _T.get("titles_search") or ["Software Engineer", "Backend Engineer", "Developer"]
# target.linkedin_locations: lista de [location, rotulo]. Default: busca global + remoto.
LOCAIS = [tuple(x) for x in (_T.get("linkedin_locations") or [["", "ANY"]])]


class Bloqueado(Exception):
    pass


class Cliente:
    def __init__(self):
        self.chamadas = 0
        self.n429 = 0
        self.erros_seguidos = 0
        self.ultimo = 0.0

    def get(self, caminho, params=None):
        espera = self.ultimo + random.uniform(*PAUSA) - time.time()
        if self.chamadas and espera > 0:
            time.sleep(espera)
        url = f"{BASE}/{caminho}" + ("?" + urllib.parse.urlencode(params) if params else "")
        for tentativa in range(3):
            self.chamadas += 1
            self.ultimo = time.time()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                    self.erros_seguidos = 0
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return ""
                if e.code in (429, 999) or e.code >= 500:
                    self.n429 += e.code in (429, 999)
                    if tentativa < 2:
                        time.sleep(ESPERA_429 * (tentativa + 1))
                        continue
                    self.erros_seguidos += 1
                    if self.erros_seguidos >= 2:
                        raise Bloqueado(f"HTTP {e.code} repetido")
                    return None
                return None
            except (urllib.error.URLError, TimeoutError) as e:
                self.erros_seguidos += 1
                if self.erros_seguidos >= 3:
                    raise Bloqueado(f"rede: {e}")
                return None
        return None


def limpa(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_busca(txt):
    vagas = []
    for bloco in re.split(r"(?=<li)", txt or ""):
        m = re.search(r"jobPosting:(\d+)", bloco)
        if not m:
            continue
        tit = re.search(r'base-search-card__title[^>]*>(.*?)</h3>', bloco, re.S)
        emp = re.search(r'base-search-card__subtitle[^>]*>(.*?)</h4>', bloco, re.S)
        loc = re.search(r'job-search-card__location[^>]*>(.*?)</span>', bloco, re.S)
        dt = re.search(r'<time[^>]*datetime="([^"]+)"', bloco)
        vagas.append({"id": m.group(1), "titulo": limpa(tit.group(1)) if tit else "", "empresa": limpa(emp.group(1)) if emp else "",
                      "local": limpa(loc.group(1)) if loc else "", "data": dt.group(1) if dt else None,
                      "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}/"})
    return vagas


def parse_detalhe(txt):
    desc = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', txt or "", re.S)
    crit = [limpa(x) for x in re.findall(r'description__job-criteria-text[^>]*>(.*?)</span>', txt or "", re.S)]
    return {"descricao": limpa(desc.group(1)) if desc else "", "criterios": crit}


def idade_dias(data):
    try:
        import datetime
        return (datetime.date.today() - datetime.date.fromisoformat(data[:10])).days
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=1, help="vagas publicadas nos últimos N dias (1, 7, 14, 30)")
    ap.add_argument("--paginas", type=int, default=2, help="páginas (10 vagas) por busca×local")
    ap.add_argument("--max-detalhes", type=int, default=25, help="quantas descrições ler no máximo")
    ap.add_argument("--min-fit", type=int, default=70)
    ap.add_argument("--buscas", nargs="*", default=BUSCAS)
    ap.add_argument("--registrar-descartes", action="store_true", help="grava no banco os knockouts achados na descrição")
    a = ap.parse_args()

    cli = Cliente()
    con = jobdb.conectar(somente_leitura=not a.registrar_descartes)
    vistas = jobdb.urls_vistas(con)
    candidatas, ids_vistos, total_cards, motivo_bloqueio = [], set(), 0, None
    cont = {"titulo": 0, "local": 0, "dedup": 0}

    try:
        for busca in a.buscas:
            for local, rotulo in LOCAIS:
                for pag in range(a.paginas):
                    params = {"keywords": busca, "f_TPR": f"r{a.dias * 86400}", "sortBy": "DD", "start": pag * 10}
                    if local:
                        params["location"] = local
                    # f_WT=2 = remoto (a API ignora na prática, mas não atrapalha)
                    params["f_WT"] = "2"
                    txt = cli.get("seeMoreJobPostings/search", params)
                    cards = parse_busca(txt)
                    total_cards += len(cards)
                    for v in cards:
                        if v["id"] in ids_vistos:
                            continue
                        ids_vistos.add(v["id"])
                        if not filtros.titulo_passa(v["titulo"]):
                            cont["titulo"] += 1
                            continue
                        if not filtros.local_passa(v["local"]):
                            cont["local"] += 1
                            continue
                        if jobdb.norm_url(v["url"]) in vistas or jobdb.dedup(con, v["url"], v["empresa"], v["titulo"]) != "NOVA":
                            cont["dedup"] += 1
                            continue
                        v["rotulo"] = rotulo
                        candidatas.append(v)
                    if len(cards) < 10:
                        break
    except Bloqueado as e:
        motivo_bloqueio = str(e)

    if total_cards == 0:
        print(f"FALLBACK_NAVEGADOR: a API pública não devolveu nenhuma vaga ({motivo_bloqueio or 'resposta vazia'}) — buscar pelo LinkedIn logado no navegador")
        sys.exit(3)

    for v in candidatas:
        v["fit"] = filtros.nota_fit(v["titulo"], v["local"], idade_dias(v["data"]))
    candidatas.sort(key=lambda v: -v["fit"])
    aprovadas, knock, lidas = [], 0, 0
    for v in candidatas:
        if lidas >= a.max_detalhes or motivo_bloqueio:
            v["obs"] = "sem descrição lida"
            aprovadas.append(v)
            continue
        try:
            det = parse_detalhe(cli.get(f"jobPosting/{v['id']}"))
        except Bloqueado as e:
            motivo_bloqueio = str(e)
            v["obs"] = "sem descrição lida"
            aprovadas.append(v)
            continue
        lidas += 1
        motivo = filtros.knockout_descricao(det["descricao"], v["local"])
        if motivo:
            knock += 1
            if a.registrar_descartes:
                jobdb.cmd_add_descarte(argparse.Namespace(empresa=v["empresa"], titulo=v["titulo"], url=v["url"],
                                                          fonte="LinkedIn (api pública)", motivo=f"auto-scan: {motivo}", data=None))
            continue
        v["fit"] = filtros.nota_fit(v["titulo"], v["local"], idade_dias(v["data"]), det["descricao"])
        v["obs"] = " · ".join(c for c in det["criterios"][:2] if c)
        aprovadas.append(v)

    aprovadas.sort(key=lambda v: -v["fit"])
    mostradas = [v for v in aprovadas if v["fit"] >= a.min_fit]
    for v in mostradas:
        print(f"LI|{v['empresa']}|{v['titulo']}|{v['local']} ({v['rotulo']})|{v['url']}|fit={v['fit']}|{v.get('obs', '')}"[:300])
    print(f"# cards: {total_cards} (únicos {len(ids_vistos)}) | cortadas: título {cont['titulo']}, local {cont['local']}, "
          f"já vistas {cont['dedup']} | descrições lidas: {lidas}, knockout: {knock} | "
          f"para aplicar (fit>={a.min_fit}): {len(mostradas)} | chamadas: {cli.chamadas} (429: {cli.n429})"
          + (f" | AVISO bloqueio parcial: {motivo_bloqueio}" if motivo_bloqueio else ""))


if __name__ == "__main__":
    main()
