#!/usr/bin/env python3
"""
E5 — Mide p50/p99 sobre PostgreSQL primario + réplica de lectura.

A diferencia de la versión anterior, aquí SÍ hay dos nodos reales conectados
por streaming replication (ver docker-compose.yml, profile "e5"):

    - pg-primary : acepta lecturas y escrituras.
    - pg-replica : standby async, solo lecturas (aplica el WAL que llega
                   de pg-primary; puede tener lag real, no simulado).

Por eso las escrituras SIEMPRE van al primario (una réplica física no admite
INSERT/UPDATE). Lo que se compara es:

    read  / primary  -> leer en el nodo que también escribe
    read  / replica  -> leer en el standby (puede ver un total desactualizado
                         si la réplica no ha aplicado el último UPDATE)
    write / primary  -> único lugar posible para escribir

Esto reemplaza al "local"/"remote" de la versión anterior, que en realidad
usaba la misma conexión con dos nombres distintos.

Uso (desde el host):
    make p1-pg-e5-setup
    make p1-pg-e5-latency
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
    operation: str  # "read" | "write"
    node: str        # "primary" | "replica"
    region: str       # solo se usa para elegir la fila del seed


CASES = (
    Case("read",  "primary", "tienda-a"),
    Case("read",  "replica", "tienda-b"),
    Case("write", "primary", "tienda-a"),
)


def connect(host_env: str, default_host: str) -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get(host_env, default_host),
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
                f"No existe fila seed para {case.region} en nodo '{case.node}'. "
                "Ejecute 'make p1-pg-e5-setup' primero y espere a que la réplica "
                "termine el clonado inicial."
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

    print(f"=== E5 · PostgreSQL primario + réplica · warmup={args.warmup} · n={args.runs} ===")

    conns = {
        "primary": connect("PGHOST_PRIMARY", "pg-primary"),
        "replica": connect("PGHOST_REPLICA", "pg-replica"),
    }

    summaries: list[dict] = []
    raw:       list[dict] = []

    try:
        for case in CASES:
            conn = conns[case.node]
            samples = measure(conn, case, args.warmup, args.runs)
            for run, ms in enumerate(samples, start=1):
                raw.append({
                    "operation": case.operation,
                    "node":      case.node,
                    "home_region": case.region,
                    "run": run,
                    "latency_ms": f"{ms:.3f}",
                })
            summaries.append({
                "operation":   case.operation,
                "node":        case.node,
                "home_region": case.region,
                "n":           len(samples),
                "p50_ms":      statistics.median(samples),
                "p99_ms":      percentile_nearest_rank(samples, 0.99),
            })
    finally:
        for conn in conns.values():
            conn.close()

    print(f"\n{'operation':10} {'node':10} {'home_region':12} {'n':>2} {'p50_ms':>8} {'p99_ms':>8}")
    print("-" * 58)
    for r in summaries:
        print(
            f"{r['operation']:10} {r['node']:10} {r['home_region']:12} "
            f"{r['n']:>2} {r['p50_ms']:>8.3f} {r['p99_ms']:>8.3f}"
        )

    os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=raw[0].keys())
        writer.writeheader()
        writer.writerows(raw)
    print(f"\nMuestras crudas: {args.csv}")
    print(
        "\nNota: 'write/primary' es la única escritura posible (la réplica es solo"
        " lectura). 'read/replica' refleja el lag real de streaming replication,"
        " no una simulación."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())