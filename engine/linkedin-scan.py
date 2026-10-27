#!/usr/bin/env python3
# Aplica — finds LinkedIn jobs through the public jobs-guest API (NO login, never uses the user's
# account), reads each candidate's description, applies dedup + config knockouts + the ghost-job
# check and returns only what is worth opening in the browser.
#
# Usage: python linkedin-scan.py [--days 1] [--pages 2] [--max-details 25] [--min-fit 70]
# Output: LI|company|title|location|url|fit=NN|ghost=NN|notes  + a final summary line.
# Exit 0 = ok (list may be empty) · 3 = FALLBACK_BROWSER (the API returned nothing)
#
# Search terms (SEARCHES) = config target.titles_search. Locations (LOCATIONS) = config
# target.linkedin_locations (default: no restriction + remote). Tight per-IP limit: ~7s+ between calls.
import argparse, html, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request
import filters, jobdb
import config

BASE = os.environ.get("LI_GUEST_BASE", "https://www.linkedin.com/jobs-guest/jobs/api")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8"}
PAUSE = (float(os.environ.get("LI_PAUSE_MIN", 9)), float(os.environ.get("LI_PAUSE_MAX", 13)))
WAIT_429 = float(os.environ.get("LI_WAIT_429", 60))

_T = config.load_config().get("target") or {}
SEARCHES = _T.get("titles_search") or ["Software Engineer", "Backend Engineer", "Developer"]


def _location_pair(x):
    """Accept 'São Paulo', ['São Paulo'] or ['São Paulo', 'SP'] and normalize to (location, label)."""
    if isinstance(x, str):
        return (x, x or "ANY")
    seq = list(x) if isinstance(x, (list, tuple)) else [str(x)]
    loc = seq[0] if seq else ""
    label = seq[1] if len(seq) > 1 else (loc or "ANY")
    return (loc, label)


# target.linkedin_locations: list of [location, label]. Default: global search + remote.
LOCATIONS = [_location_pair(x) for x in (_T.get("linkedin_locations") or [["", "ANY"]])]


class Blocked(Exception):
    pass


class Client:
    def __init__(self):
        self.calls = 0
        self.n429 = 0
        self.errors_in_row = 0
        self.last = 0.0

    def get(self, route, params=None):
        wait = self.last + random.uniform(*PAUSE) - time.time()
        if self.calls and wait > 0:
            time.sleep(wait)
        url = f"{BASE}/{route}" + ("?" + urllib.parse.urlencode(params) if params else "")
        for attempt in range(3):
            self.calls += 1
            self.last = time.time()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                    self.errors_in_row = 0
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return ""
                if e.code in (429, 999) or e.code >= 500:
                    self.n429 += e.code in (429, 999)
                    if attempt < 2:
                        time.sleep(WAIT_429 * (attempt + 1))
                        continue
                    self.errors_in_row += 1
                    if self.errors_in_row >= 2:
                        raise Blocked(f"HTTP {e.code} repeated")
                    return None
                return None
            except (urllib.error.URLError, TimeoutError) as e:
                self.errors_in_row += 1
                if self.errors_in_row >= 3:
                    raise Blocked(f"network: {e}")
                return None
        return None


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_search(txt):
    jobs = []
    for block in re.split(r"(?=<li)", txt or ""):
        m = re.search(r"jobPosting:(\d+)", block)
        if not m:
            continue
        tit = re.search(r'base-search-card__title[^>]*>(.*?)</h3>', block, re.S)
        comp = re.search(r'base-search-card__subtitle[^>]*>(.*?)</h4>', block, re.S)
        loc = re.search(r'job-search-card__location[^>]*>(.*?)</span>', block, re.S)
        dt = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        jobs.append({"id": m.group(1), "title": clean(tit.group(1)) if tit else "", "company": clean(comp.group(1)) if comp else "",
                     "location": clean(loc.group(1)) if loc else "", "date": dt.group(1) if dt else None,
                     "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}/"})
    return jobs


def parse_detail(txt):
    desc = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', txt or "", re.S)
    crit = [clean(x) for x in re.findall(r'description__job-criteria-text[^>]*>(.*?)</span>', txt or "", re.S)]
    return {"description": clean(desc.group(1)) if desc else "", "criteria": crit}


def age_days(date):
    try:
        import datetime
        return (datetime.date.today() - datetime.date.fromisoformat(date[:10])).days
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1, help="jobs posted in the last N days (1, 7, 14, 30)")
    ap.add_argument("--pages", type=int, default=2, help="pages (10 jobs) per search×location")
    ap.add_argument("--max-details", type=int, default=25, help="max descriptions to read")
    ap.add_argument("--min-fit", type=int, default=70)
    ap.add_argument("--searches", nargs="*", default=SEARCHES)
    ap.add_argument("--record-discards", action="store_true", help="store the description knockouts found in the database")
    a = ap.parse_args()

    cli = Client()
    con = jobdb.connect()
    seen_db = jobdb.seen_urls(con)
    candidates, ids_seen, total_cards, block_reason = [], set(), 0, None
    cut = {"title": 0, "location": 0, "dedup": 0}

    try:
        for search in a.searches:
            for location, label in LOCATIONS:
                for page in range(a.pages):
                    params = {"keywords": search, "f_TPR": f"r{a.days * 86400}", "sortBy": "DD", "start": page * 10}
                    if location:
                        params["location"] = location
                    # f_WT=2 = remote (the API mostly ignores it, but it does not hurt)
                    params["f_WT"] = "2"
                    txt = cli.get("seeMoreJobPostings/search", params)
                    cards = parse_search(txt)
                    total_cards += len(cards)
                    for v in cards:
                        if v["id"] in ids_seen:
                            continue
                        ids_seen.add(v["id"])
                        if not filters.title_ok(v["title"]) or not filters.company_ok(v["company"]):
                            cut["title"] += 1
                            continue
                        if not filters.location_ok(v["location"]):
                            cut["location"] += 1
                            continue
                        jobdb.record_seen(con, v["company"], v["title"], v["url"])
                        if jobdb.norm_url(v["url"]) in seen_db or jobdb.dedup(con, v["url"], v["company"], v["title"]) != "NEW":
                            cut["dedup"] += 1
                            continue
                        v["label"] = label
                        candidates.append(v)
                    if len(cards) < 10:
                        break
    except Blocked as e:
        block_reason = str(e)
    con.commit()

    if total_cards == 0:
        print(f"FALLBACK_BROWSER: the public API returned no jobs ({block_reason or 'empty response'}) — search through the logged-in LinkedIn in the browser")
        sys.exit(3)

    for v in candidates:
        v["fit"] = filters.fit_score(v["title"], v["location"], age_days(v["date"]))
    candidates.sort(key=lambda v: -v["fit"])
    approved, knocked, ghosts, read = [], 0, 0, 0
    for v in candidates:
        times, span = jobdb.seen_stats(con, v["company"], v["title"])
        if read >= a.max_details or block_reason:
            v["ghost"] = filters.ghost_score(title=v["title"], age_days=age_days(v["date"]), times_seen=times, seen_span_days=span)
            v["notes"] = "description not read"
            if v["ghost"] < filters.GHOST_MAX:
                approved.append(v)
            else:
                ghosts += 1
            continue
        try:
            det = parse_detail(cli.get(f"jobPosting/{v['id']}"))
        except Blocked as e:
            block_reason = str(e)
            v["ghost"] = 0
            v["notes"] = "description not read"
            approved.append(v)
            continue
        read += 1
        reason = filters.description_knockout(det["description"], v["location"])
        v["ghost"] = filters.ghost_score(title=v["title"], text=det["description"], age_days=age_days(v["date"]),
                                         times_seen=times, seen_span_days=span)
        if not reason and v["ghost"] >= filters.GHOST_MAX:
            reason = f"ghost job (score {v['ghost']})"
            ghosts += 1
        elif reason:
            knocked += 1
        if reason:
            if a.record_discards:
                jobdb.cmd_add_discard(type("A", (), dict(company=v["company"], title=v["title"], url=v["url"],
                                                         source="LinkedIn (public api)", reason=f"auto-scan: {reason}", date=None)))
            continue
        v["fit"] = filters.fit_score(v["title"], v["location"], age_days(v["date"]), det["description"])
        v["notes"] = " · ".join(c for c in det["criteria"][:2] if c)
        approved.append(v)

    approved.sort(key=lambda v: -v["fit"])
    shown = [v for v in approved if v["fit"] >= a.min_fit]
    for v in shown:
        print(f"LI|{v['company']}|{v['title']}|{v['location']} ({v['label']})|{v['url']}|fit={v['fit']}|ghost={v['ghost']}|{v.get('notes', '')}"[:320])
    print(f"# cards: {total_cards} (unique {len(ids_seen)}) | cut: title {cut['title']}, location {cut['location']}, "
          f"already seen {cut['dedup']} | descriptions read: {read}, knockout: {knocked}, ghost: {ghosts} | "
          f"to apply (fit>={a.min_fit}): {len(shown)} | calls: {cli.calls} (429: {cli.n429})"
          + (f" | WARNING partial block: {block_reason}" if block_reason else ""))


if __name__ == "__main__":
    main()
