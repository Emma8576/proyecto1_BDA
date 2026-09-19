#!/usr/bin/env python3
"""Mide p50/p99 de operaciones locales y remotas desde un gateway fijo."""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import time
from dataclasses import dataclass

import psycopg

# Registro de UUIDs
ROWS = {
    "tienda-a": "10000000-0000-0000-0000-000000000001",
    "tienda-b": "10000000-0000-0000-0000-000000000002",
    "cd-central": "10000000-0000-0000-0000-000000000003",
}


@dataclass(frozen=True)
class Case:
    operation: str
    locality: str
    region: str


CASES = (
    Case("read", "local", "tienda-a"),
    Case("read", "remote", "tienda-b"),
    Case("write", "local", "tienda-a"),
    Case("write", "remote", "tienda-b"),
)


def connect(host: str, port: int) -> psycopg.Connection:
    return psycopg.connect(
        host=host,
        port=port,
        user="root",
        dbname="ti4601",
        sslmode="disable",
        connect_timeout=3,
        autocommit=True,
    )


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def execute_case(conn: psycopg.Connection, case: Case) -> None:
    pedido_id = ROWS[case.region]
    if case.operation == "read":
        row = conn.execute(
            """
            SELECT total, estado
            FROM pedido
            WHERE region = %s AND pedido_id = %s
            """,
            (case.region, pedido_id),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"No existe fila seed para {case.region}")
    else:
        conn.execute(
            """
            UPDATE pedido
            SET total = total + 0.01
            WHERE region = %s AND pedido_id = %s
            """,
            (case.region, pedido_id),
        )


def measure(
    conn: psycopg.Connection, case: Case, warmup: int, runs: int
) -> list[float]:
    for _ in range(warmup):
        execute_case(conn, case)

    samples: list[float] = []
    for _ in range(runs):
        started = time.perf_counter_ns()
        execute_case(conn, case)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        samples.append(elapsed_ms)
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway", default="localhost", help="Host del gateway (ej. localhost o ti4601-crdb-1)")
    parser.add_argument("--port", type=int, default=26257, help="Puerto SQL")
    parser.add_argument("--runs", type=int, default=50, help="Número de corridas (mínimo 30)")
    parser.add_argument("--warmup", type=int, default=5, help="Corridas de calentamiento descartadas")
    parser.add_argument("--csv", default="evidence/mediciones_e3.csv", help="Ruta para guardar muestras crudas CSV")
    args = parser.parse_args()
    if args.runs < 30:
        parser.error("--runs debe ser >= 30 para el entregable")
    if args.warmup < 1:
        parser.error("--warmup debe ser >= 1")

    print(
        f"=== Proyecto 1 · gateway={args.gateway} · "
        f"warmup={args.warmup} · n={args.runs} ==="
    )
    summaries: list[dict[str, str | int | float]] = []
    raw: list[dict[str, str | int | float]] = []

    with connect(args.gateway, args.port) as conn:
        gateway_region = conn.execute(
            "SELECT gateway_region()"
        ).fetchone()[0]
        print(f"Región del gateway: {gateway_region}")
        for case in CASES:
            samples = measure(conn, case, args.warmup, args.runs)
            for run, elapsed_ms in enumerate(samples, start=1):
                raw.append(
                    {
                        "operation": case.operation,
                        "locality": case.locality,
                        "home_region": case.region,
                        "run": run,
                        "latency_ms": f"{elapsed_ms:.3f}",
                    }
                )
            summaries.append(
                {
                    "operation": case.operation,
                    "locality": case.locality,
                    "home_region": case.region,
                    "n": len(samples),
                    "p50_ms": statistics.median(samples),
                    "p99_ms": percentile_nearest_rank(samples, 0.99),
                }
            )

    print("\noperation locality home_region n p50_ms p99_ms")
    print("-" * 58)
    for row in summaries:
        print(
            f"{row['operation']:10} {row['locality']:10} "
            f"{row['home_region']:12} {row['n']:>2} "
            f"{row['p50_ms']:>8.3f} {row['p99_ms']:>8.3f}"
        )

    if args.csv:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=raw[0].keys())
            writer.writeheader()
            writer.writerows(raw)
        print(f"\nMuestras crudas: {args.csv}")

    print(
        "\nNota: Al correr las 3 regiones en una sola máquina, los tiempos locales/remotos "
        "serán muy similares a menos que se aplique simulación de latencia de red."
    )
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

