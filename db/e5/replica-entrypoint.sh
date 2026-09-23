#!/bin/bash
# Entrypoint del contenedor pg-replica.
#
# La imagen oficial de postgres no sabe clonarse desde otro nodo por sí sola;
# en el primer arranque (volumen vacío) este script hace un pg_basebackup
# contra pg-primary y deja standby.signal + primary_conninfo (flag -R),
# de modo que al ceder el control a docker-entrypoint.sh el proceso arranca
# ya en modo standby, aplicando el WAL que llega por streaming replication.
set -euo pipefail

PGDATA_DIR="${PGDATA:-/var/lib/postgresql/data}"

mkdir -p "$PGDATA_DIR"
chown -R postgres:postgres "$PGDATA_DIR"

if [ -z "$(ls -A "$PGDATA_DIR" 2>/dev/null)" ]; then
    echo "[replica] esperando a que pg-primary acepte conexiones de replicación..."
    until PGPASSWORD=replicator gosu postgres pg_isready -h pg-primary -U replicator -d ti4601 >/dev/null 2>&1; do
        sleep 1
    done

    echo "[replica] pg_basebackup desde pg-primary..."
    PGPASSWORD=replicator gosu postgres pg_basebackup \
        -h pg-primary -U replicator \
        -D "$PGDATA_DIR" -Fp -Xs -P -R

    chown -R postgres:postgres "$PGDATA_DIR"
    chmod 0700 "$PGDATA_DIR"
    echo "[replica] clonado completo; standby.signal creado por -R."
fi

exec docker-entrypoint.sh postgres