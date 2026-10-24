#!/usr/bin/env python3
# Aplica — travas de segurança por SCRIPT (não "de cabeça"). O LLM conta errado em contexto
# longo, e esta é a trava que não pode falhar. O SKILL.md chama este script a cada lote e OBEDECE
# a saída. Se o script e o placar mental divergirem, o SCRIPT vence (conta o banco real).
# Tetos vêm de config.json (caps.applications_per_day, caps.max_batches).
#
# Uso:  python caps.py --lote <n> --candidaturas <total_hoje>
# Saída (última linha, parseável): CONTINUAR | PARAR:lote-max | PARAR:teto-candidaturas | PARAR:db-indisponivel
import argparse, datetime, sqlite3
import config
import jobdb


def conta_hoje(hoje_iso):
    # incertas não contam no teto (regra do SKILL.md)
    con = jobdb.conectar(somente_leitura=True)
    return con.execute("SELECT COUNT(*) FROM candidaturas WHERE data=? AND status<>'incerta'", (hoje_iso,)).fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", type=int, required=True)
    ap.add_argument("--candidaturas", type=int, required=True, help="total de candidaturas de hoje pelo placar do orquestrador")
    ap.add_argument("--data", default=None, help="AAAA-MM-DD; default = hoje")
    args = ap.parse_args()

    # A trava nunca pode dar traceback: config malformado falha-FECHADO (PARAR), nunca "open".
    try:
        caps = config.load_config().get("caps") or {}

        def _cap_int(k, d):
            v = caps.get(k, d)
            return int(v) if v is not None else d

        teto_candidaturas = _cap_int("applications_per_day", 15)
        max_lotes = _cap_int("max_batches", 10)
    except Exception as e:
        print(f"PARAR:config-invalida ({e})")
        return

    hoje = args.data or datetime.date.today().isoformat()
    try:
        banco_n = conta_hoje(hoje)
    except (sqlite3.Error, SystemExit):
        print("PARAR:db-indisponivel")
        return

    # O teto usa o MAIOR entre o placar e a contagem do banco (conservador: nunca estourar sem perceber).
    efetivo = max(args.candidaturas, banco_n)

    print(f"# data={hoje} lote={args.lote}/{max_lotes} candidaturas_placar={args.candidaturas} "
          f"banco_hoje={banco_n} efetivo={efetivo}/{teto_candidaturas}")

    if args.lote >= max_lotes:
        print("PARAR:lote-max")
        return
    if efetivo >= teto_candidaturas:
        print("PARAR:teto-candidaturas")
        return
    print("CONTINUAR")


if __name__ == "__main__":
    main()
