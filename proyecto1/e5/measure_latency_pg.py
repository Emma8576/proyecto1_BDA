#!/usr/bin/env python3
"""
E5 — Mide p50/p99 sobre PostgreSQL para comparar con los números de E3 (CockroachDB).

Corre las mismas 4 operaciones que measure_latency.py pero contra el servicio
`postgres` del docker-compose. No existe concepto de región ni gateway_region(),
así que "local" y "remote" son la misma conexión — el punto es medir el costo
base sin consenso Raft.

Uso (desde el host):
    docker compose run --rm app \
      python3 proyecto1/measure_latency_pg.py --runs 50 \
      | tee evidence/mediciones_e5_pg.txt
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import time
from dataclasses import dataclass

import psycopg

ROWS = {
    "tienda-a":   "10000000-0000-0000-0000-000000000001",
    "tienda-b":   "10000000-0000-0000-0000-000000000002",
    "cd-central": "10000000-0000-0000-0000-000000000003",
}


@dataclass(frozen=True)
class Case:
    operation: str
    locality: str   # "local" / "remote" — semántico, no real en PG
    region: str


CASES = (
    Case("read",  "local",  "tienda-a"),
    Case("read",  "remote", "tienda-b"),
    Case("write", "local",  "tienda-a"),
    Case("write", "remote", "tienda-b"),
)


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("PGHOST", "postgres"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ.get("PGUSER", "ti4601"),
        password=os.environ.get("PGPASSWORD", "ti4601"),
        dbname=os.environ.get("PGDATABASE", "ti4601"),
        connect_timeout=3,
        autocommit=True,
    )


def percentile_nearest_rank(values: list[float], p: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(p * len(ordered)))
    return ordered[rank - 1]


def execute_case(conn: psycopg.Connection, case: Case) -> None:
    pedido_id = ROWS[case.region]
    if case.operation == "read":
        row = conn.execute(
            "SELECT total, estado FROM pedido WHERE pedido_id = %s",
            (pedido_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                f"No existe fila seed para {case.region}. "
                "Ejecute proyecto1/seed.sql sobre PostgreSQL primero."
            )
    else:
        conn.execute(
            "UPDATE pedido SET total = total + 0.01 WHERE pedido_id = %s",
            (pedido_id,),
        )


def measure(conn: psycopg.Connection, case: Case, warmup: int, runs: int) -> list[float]:
    for _ in range(warmup):
        execute_case(conn, case)
    samples: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        execute_case(conn, case)
        samples.append((time.perf_counter_ns() - t0) / 1_000_000)
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs",   type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--csv", default="evidence/mediciones_e5_pg.csv")
    args = parser.parse_args()

    print(f"=== E5 · PostgreSQL primario · warmup={args.warmup} · n={args.runs} ===")

    summaries: list[dict] = []
    raw:       list[dict] = []

    with connect() as conn:
        for case in CASES:
            samples = measure(conn, case, args.warmup, args.runs)
            for run, ms in enumerate(samples, start=1):
                raw.append({
                    "operation": case.operation,
                    "locality":  case.locality,
                    "home_region": case.region,
                    "run": run,
                    "latency_ms": f"{ms:.3f}",
                })
            summaries.append({
                "operation":   case.operation,
                "locality":    case.locality,
                "home_region": case.region,
                "n":           len(samples),
                "p50_ms":      statistics.median(samples),
                "p99_ms":      percentile_nearest_rank(samples, 0.99),
            })

    print(f"\n{'operation':10} {'locality':10} {'home_region':12} {'n':>2} {'p50_ms':>8} {'p99_ms':>8}")
    print("-" * 58)
    for r in summaries:
        print(
            f"{r['operation']:10} {r['locality']:10} {r['home_region']:12} "
            f"{r['n']:>2} {r['p50_ms']:>8.3f} {r['p99_ms']:>8.3f}"
        )

    os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=raw[0].keys())
        writer.writeheader()
        writer.writerows(raw)
    print(f"\nMuestras crudas: {args.csv}")
    print(
        "\nNota: En PostgreSQL no hay separación de regiones — 'local' y 'remote'"
        " usan la misma conexión. Los números miden el costo base sin Raft."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())