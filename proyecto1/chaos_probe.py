#!/usr/bin/env python3
"""Sonda de escrituras para medir disponibilidad durante una falla de nodo."""

from __future__ import annotations

import argparse
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg

# ========================================================================
# Helpers
# ========================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def connect() -> psycopg.Connection:
    hosts = os.environ.get("PGHOST", "crdb-1")
    port  = os.environ.get("PGPORT", "26257")
    user  = os.environ.get("PGUSER", "root")
    pwd   = os.environ.get("PGPASSWORD", "")
    db    = os.environ.get("PGDATABASE", "ti4601")
    ssl   = os.environ.get("PGSSLMODE", "disable")

    dsn = (
        f"host={hosts} port={port} user={user} password={pwd} "
        f"dbname={db} sslmode={ssl} "
        f"connect_timeout=2 options='-c statement_timeout=2000'"
    )
    return psycopg.connect(dsn, autocommit=True)


def write_once() -> int:
    with connect() as conn:
        row = conn.execute(
            """
            UPDATE ti4601.public.stock_probe
               SET version    = version + 1,
                   updated_at = now()
             WHERE id = 1
            RETURNING version
            """
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "No existe stock_probe(id=1). "
                "Aplique chaos_probe_setup.sql antes de ejecutar la sonda."
            )
        return row[0]

def read_signal(path: Path) -> float | None:
    
    try:
        return float(path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None

# ========================================================================
# Main
# ========================================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="E4 — sonda de escrituras para chaos testing (proyecto tiendas)"
    )
    parser.add_argument(
        "--duration", type=float, default=40,
        help="Segundos totales de ejecución (default: 40)"
    )
    parser.add_argument(
        "--interval", type=float, default=0.5,
        help="Intervalo entre intentos en segundos (default: 0.5)"
    )
    parser.add_argument(
        "--label", default="E4",
        help="Etiqueta para el log (default: E4)"
    )
    parser.add_argument(
        "--signal-file", default="evidence/chaos-e4-stop.epoch",
        help="Archivo de señal que el operador crea inmediatamente tras docker stop"
    )
    parser.add_argument(
        "--csv", default="evidence/chaos-e4.csv",
        help="Archivo CSV de salida con todas las muestras"
    )
    args = parser.parse_args()

    signal_path = Path(args.signal_file)
    output_path = Path(args.csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    samples: list[dict] = []
    first_ok_after_signal: float | None = None
    failures_after_signal = 0
    last_confirmed_version: int | None = None

    print(f"=== Proyecto 1 · Sonda {args.label} — E4 Chaos Testing ===")
    print(f"PGHOST={os.environ.get('PGHOST', 'crdb-1')}")
    print("Tabla objetivo: ti4601.public.stock_probe(id=1)  RF=3")
    print(f"Duración: {args.duration}s  |  Intervalo: {args.interval}s")
    print(f"Señal de falla: {signal_path}")
    print(f"CSV de salida:  {output_path}")
    print("-" * 72)
    print(f"{'timestamp_utc':<32} {'phase':<12} {'status':<6} {'latency_ms':>10}  error")
    print("-" * 72)

    while time.time() - started < args.duration:
        attempt_started = time.time()
        perf_start = time.perf_counter_ns()

        status = "ok"
        error  = ""
        version_written: int | None = None

        try:
            version_written = write_once()
            last_confirmed_version = version_written
        except Exception as exc:
            status = "error"
            error  = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"[:240]

        latency_ms   = (time.perf_counter_ns() - perf_start) / 1_000_000
        completed_at = time.time()

        signal_at = read_signal(signal_path)
        phase = "before-stop"
        if signal_at is not None and completed_at >= signal_at:
            phase = "after-stop"
            if status == "error":
                failures_after_signal += 1
            elif first_ok_after_signal is None:
                first_ok_after_signal = completed_at

        sample = {
            "timestamp_utc":   utc_now(),
            "epoch":           f"{attempt_started:.6f}",
            "completed_epoch": f"{completed_at:.6f}",
            "phase":           phase,
            "status":          status,
            "latency_ms":      f"{latency_ms:.3f}",
            "version":         str(version_written) if version_written is not None else "",
            "error":           error,
        }
        samples.append(sample)

        ver_str = f"v={version_written}" if version_written else ""
        print(
            f"{sample['timestamp_utc']:<32} {phase:<12} {status:<6} "
            f"{latency_ms:>10.3f} ms  {ver_str}  {error}"
        )

        elapsed = time.time() - attempt_started
        time.sleep(max(0.0, args.interval - elapsed))

    # ========================================================================
    # Escribir CSV
    # ========================================================================
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(samples[0].keys()))
        writer.writeheader()
        writer.writerows(samples)

    # ========================================================================
    # Resumen RTO / RPO
    # ========================================================================
    signal_at = read_signal(signal_path)

    print("\n" + "=" * 72)
    print(f"Muestras: {output_path}")
    print(f"Errores después de la señal de falla: {failures_after_signal}")

    if signal_at is None:
        print("RTO no calculado: nunca apareció el archivo de señal.")
    elif first_ok_after_signal is None:
        print("RTO no observado: no hubo escritura OK después de la señal.")
    else:
        rto_ms = max(0.0, (first_ok_after_signal - signal_at) * 1000)
        print(f"RTO observado (primera escritura OK post-falla): {rto_ms:.1f} ms")
    print(
        "RPO se verifica después: la fila committed anterior debe seguir "
        "presente y su version no debe retroceder."
    )
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())