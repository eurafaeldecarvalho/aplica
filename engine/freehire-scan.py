#!/usr/bin/env python3
# Aplica — finds jobs on the freehire.me aggregator (public JSON API, ~50 ATSs), applies dedup +
# config knockouts + the ghost-job check and returns the ones worth opening. Same output as the other scans.
#
# Usage: python freehire-scan.py [--days 3] [--pages 3] [--min-fit 70]
# Output: FH|company|title|location|url|fit=NN|ghost=NN  + a summary line.
# Exit 0 = ok · 4 = SOURCE_UNAVAILABLE (the routine just skips this source).
#
# Search terms and target skills come from the config (target.titles_search / target.stack_target).
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
import filters, jobdb
import config

BASE = os.environ.get("FREEHIRE_API_URL", "https://freehire.me")
_T = config.load_config().get("target") or {}
# search terms: last word of each target title, lowercase, deduplicated
SEARCHES = _T.get("freehire_queries") or list(dict.fromkeys(s.split()[-1].lower() for s in (_T.get("titles_search") or ["developer"]) if s.split()))[:4] or ["developer"]
# target skills: alphanumeric words pulled from the config's stack_target regex
TARGET_SKILLS = {w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9.]+", _T.get("stack_target") or "") if len(w) > 1}
_LANG_CODE = {"english": "en", "portuguese": "pt", "ingles": "en", "portugues": "pt", "spanish": "es"}
LANGS_OK = {_LANG_CODE.get(l.lower(), l[:2].lower()) for l in (_T.get("work_language") or ["english", "portuguese"])} | {None, ""}


def search(params):
    url = f"{BASE}/api/v1/agent/jobs/search?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "aplica/1.0"}), timeout=30) as r:
                try:
                    return json.load(r)
                except ValueError as e:
                    # non-JSON response (WAF/error HTML with status 200) → source unavailable, not a crash
                    raise ConnectionError(f"freehire returned non-JSON: {e}") from e
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            # 4xx (403/404/etc.) is not recoverable → source unavailable (exit 4), not exit 1
            raise ConnectionError(f"freehire HTTP {e.code}: {url[:120]}") from e
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (attempt + 1))
    raise ConnectionError(f"freehire unavailable: {url[:120]}")


def clean_text(s):
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def evaluate(j):
    """(passes, reason) for a freehire job, before dedup."""
    title, loc = j.get("title") or "", j.get("location") or ""
    if not filters.title_ok(title):
        return False, "title"
    if not filters.company_ok(j.get("company") or ""):
        return False, "blocked-company"
    if not filters.location_ok(loc):
        return False, "location"
    enr = j.get("enrichment") or {}
    if LANGS_OK and enr.get("posting_language") not in LANGS_OK:
        return False, "language"
    skills = {s.lower() for s in (j.get("skills") or [])}
    if TARGET_SKILLS and skills and not skills & TARGET_SKILLS:
        return False, "stack"
    if filters.description_knockout(clean_text(j.get("description")), loc):
        return False, "description"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--pages", type=int, default=3, help="pages of 50 per search")
    ap.add_argument("--min-fit", type=int, default=70)
    a = ap.parse_args()

    con = jobdb.connect()
    seen_db = jobdb.seen_urls(con)
    seen, approved, cut, total = set(), [], {}, 0
    try:
        for q in SEARCHES:
            for page in range(a.pages):
                d = search({"q": q, "limit": 50, "offset": page * 50, "posted_within_days": a.days,
                            "work_mode": "remote", "description_format": "text"})
                items = d.get("data") or []
                total += len(items)
                for j in items:
                    url = j.get("url") or ""
                    if url in seen:
                        continue
                    seen.add(url)
                    ok, reason = evaluate(j)
                    if not ok:
                        cut[reason] = cut.get(reason, 0) + 1
                        continue
                    jobdb.record_seen(con, j.get("company"), j.get("title"), url)
                    if jobdb.norm_url(url) in seen_db or jobdb.dedup(con, url, j.get("company"), j.get("title")) != "NEW":
                        cut["already seen"] = cut.get("already seen", 0) + 1
                        continue
                    reality = j.get("reality") or {}
                    age = reality.get("age_days")
                    desc = clean_text(j.get("description"))
                    times, span = jobdb.seen_stats(con, j.get("company"), j.get("title"))
                    ghost = filters.ghost_score(title=j.get("title"), text=desc, age_days=age, times_seen=times,
                                                seen_span_days=span, fake_freshness=bool(reality.get("fake_freshness")))
                    if ghost >= filters.GHOST_MAX:
                        cut["ghost"] = cut.get("ghost", 0) + 1
                        continue
                    loc = j.get("location") or "/".join(j.get("regions") or [])
                    fit = filters.fit_score(j.get("title"), loc + " " + " ".join(j.get("regions") or []), age, desc)
                    approved.append((fit, ghost, j, loc))
                if len(items) < 50:
                    break
    except ConnectionError as e:
        if not total:
            print(f"SOURCE_UNAVAILABLE: {e}")
            sys.exit(4)
        cut["partial error"] = 1
    con.commit()

    approved.sort(key=lambda t: -t[0])
    shown = [t for t in approved if t[0] >= a.min_fit]
    for fit, ghost, j, loc in shown:
        print(f"FH|{j.get('company')}|{j.get('title')}|{loc}|{j.get('url')}|fit={fit}|ghost={ghost}"[:320])
    print(f"# freehire: {total} results ({len(seen)} unique) | cut: "
          + (", ".join(f"{k} {v}" for k, v in sorted(cut.items())) or "none") + f" | to apply (fit>={a.min_fit}): {len(shown)}")


if __name__ == "__main__":
    main()
