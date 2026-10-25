#!/usr/bin/env python3
# Aplica — safety caps enforced by SCRIPT (not "in the head"). The LLM miscounts in long contexts,
# and this is the guard that cannot fail. The SKILL.md calls this script before every batch and
# OBEYS its output. If the script and the mental tally disagree, the SCRIPT wins (it counts the real DB).
# Caps come from config.json (caps.applications_per_day, caps.max_batches).
#
# Usage:  python caps.py --batch <n> --applications <total_today>
# Output (last line, parseable): CONTINUE | STOP:max-batches | STOP:daily-cap | STOP:db-unavailable | STOP:invalid-config
import argparse, datetime, sqlite3
import config
import jobdb


def count_today(day_iso):
    # uncertain applications do not count toward the cap (SKILL.md rule)
    con = jobdb.connect(read_only=True)
    return con.execute("SELECT COUNT(*) FROM applications WHERE date=? AND status<>'uncertain'", (day_iso,)).fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, required=True)
    ap.add_argument("--applications", type=int, required=True, help="today's applications per the orchestrator's tally")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; default = today")
    args = ap.parse_args()

    # The guard must never traceback: a malformed config fails CLOSED (STOP), never open.
    try:
        caps = config.load_config().get("caps") or {}

        def _cap_int(k, d):
            v = caps.get(k, d)
            return int(v) if v is not None else d

        daily_cap = _cap_int("applications_per_day", 15)
        max_batches = _cap_int("max_batches", 10)
    except Exception as e:
        print(f"STOP:invalid-config ({e})")
        return

    day = args.date or datetime.date.today().isoformat()
    try:
        db_n = count_today(day)
    except (sqlite3.Error, SystemExit):
        print("STOP:db-unavailable")
        return

    # The cap uses the HIGHER of the tally and the DB count (conservative: never overshoot unnoticed).
    effective = max(args.applications, db_n)

    print(f"# date={day} batch={args.batch}/{max_batches} applications_tally={args.applications} "
          f"db_today={db_n} effective={effective}/{daily_cap}")

    if args.batch >= max_batches:
        print("STOP:max-batches")
        return
    if effective >= daily_cap:
        print("STOP:daily-cap")
        return
    print("CONTINUE")


if __name__ == "__main__":
    main()
