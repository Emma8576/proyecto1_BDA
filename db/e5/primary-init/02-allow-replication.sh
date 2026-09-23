#!/bin/bash
# Se ejecuta una sola vez, durante el initdb del contenedor pg-primary.
# El pg_hba.conf por defecto no permite conexiones de tipo "replication";
# sin esta línea pg_basebackup de la réplica falla con "no pg_hba.conf entry".
set -euo pipefail

echo "host replication replicator all md5" >> "$PGDATA/pg_hba.conf"