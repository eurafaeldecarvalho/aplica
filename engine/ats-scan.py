#!/usr/bin/env python3
# Aplica — public ATS API scan (Lever / Greenhouse / Ashby).
# Reads the companies from data/ats-companies.txt and prints jobs that pass the config knockouts
# (filters.py), the ghost-job check and dedup against state.db. Computes a 0-100 FIT score per job.
# The agent only opens high-fit jobs in the browser (sorted desc).
#
# Usage: python ats-scan.py [--min-fit 70]
# Output: ATS|company|title|location|url|fit=NN|ghost=NN  (+ a final summary line)
import json, urllib.request, sys, os, argparse, datetime, concurrent.futures as cf
import jobdb, filters

HERE = os.path.dirname(os.path.abspath(__file__))
COMPANIES = os.environ.get("APLICA_ATS_LIST") or os.path.join(HERE, "data", "ats-companies.txt")
NOW = datetime.datetime.now(datetime.timezone.utc)


def get(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        return json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        return None


def age_days_from(dt):
    if dt is None:
        return None
    try:
        return max(0, (NOW - dt).days)
    except Exception:
        return None


def parse_iso(s):
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        d = datetime.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return d
    except Exception:
        return None


def parse_ms(ms):
    try:
        return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    except Exception:
        return None


def lever(c):
    out = []
    for p in (get(f"https://api.lever.co/v0/postings/{c}?mode=json") or []):
        dt = parse_ms(p.get("createdAt"))
        out.append(("L", c, p.get("text", ""), p.get("categories", {}).get("location", ""), p.get("hostedUrl", ""), age_days_from(dt)))
    return out


def gh(c):
    j = get(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs") or {"jobs": []}
    out = []
    for p in j.get("jobs", []):
        dt = parse_iso(p.get("updated_at") or p.get("first_published"))
        out.append(("G", c, p.get("title", ""), (p.get("location") or {}).get("name", ""), p.get("absolute_url", ""), age_days_from(dt)))
    return out


def ash(c):
    j = get(f"https://api.ashbyhq.com/posting-api/job-board/{c}") or {"jobs": []}
    out = []
    for p in j.get("jobs", []):
        dt = parse_iso(p.get("publishedAt") or p.get("publishedDate") or p.get("updatedAt"))
        out.append(("A", c, p.get("title", ""), p.get("location", ""), p.get("jobUrl", ""), age_days_from(dt)))
    return out


FN = {"lever": lever, "greenhouse": gh, "ashby": ash}
norm_url = jobdb.norm_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-fit", type=int, default=0, help="print only jobs with fit>=N (default 0 = all)")
    args = ap.parse_args()

    tasks = []
    with open(COMPANIES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            ats, slug = line.split("|", 1)
            fn = FN.get(ats.strip().lower())
            if fn and slug.strip():
                tasks.append((fn, slug.strip()))

    con = jobdb.connect()
    applied = jobdb.seen_urls(con)

    out, empty = [], []
    with cf.ThreadPoolExecutor(16) as ex:
        for (fn, c), res in zip(tasks, ex.map(lambda t: t[0](t[1]), tasks)):
            if not res:
                empty.append(c)
                continue
            for ats, comp, title, loc, url, age in res:
                if filters.title_ok(title) and filters.company_ok(comp) and filters.location_ok(loc):
                    out.append((ats, comp, title, loc, url, age))

    seen, dedup_ledger, ghosts, rows = set(), 0, 0, []
    for ats, comp, title, loc, url, age in out:
        k = comp + "|" + title
        if k in seen:
            continue
        seen.add(k)
        jobdb.record_seen(con, comp, title, url)
        if url and norm_url(url) in applied:   # already handled (URL dedup against the database)
            dedup_ledger += 1
            continue
        times, span = jobdb.seen_stats(con, comp, title)
        ghost = filters.ghost_score(title=title, age_days=age, times_seen=times, seen_span_days=span)
        if ghost >= filters.GHOST_MAX:
            ghosts += 1
            continue
        rows.append((ats, comp, title, loc, url, filters.fit_score(title, loc, age), ghost))
    con.commit()

    rows.sort(key=lambda r: -r[5])
    n_shown = 0
    n_fit70 = sum(1 for r in rows if r[5] >= 70)
    for ats, comp, title, loc, url, fit, ghost in rows:
        if fit < args.min_fit:
            continue
        n_shown += 1
        print(f"{ats}|{comp}|{title}|{loc}|{url}|fit={fit}|ghost={ghost}"[:260])
    print(f"# MATCHES: {len(rows)} (shown: {n_shown}) | fit>=70: {n_fit70} | "
          f"dedup (already in db): {dedup_ledger} | ghost (>= {filters.GHOST_MAX}): {ghosts} | "
          f"empty/error boards: {','.join(empty) if empty else '(none)'}")


if __name__ == "__main__":
    main()
