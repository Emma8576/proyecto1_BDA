#!/usr/bin/env python3

# Verificacion basica de la configuracion del cluster.

import sys

import psycopg


EXPECTED_REGIONS = {
    "tienda-a",
    "tienda-b",
    "cd-central",
}


def live_regions(conn):

    rows = conn.execute(
        """
        SELECT locality
        FROM crdb_internal.gossip_nodes
        WHERE is_live
        """
    ).fetchall()

    regions = set()

    for row in rows:

        locality = str(row[0])

        for item in locality.split(","):

            if item.startswith("region="):
                regions.add(item.removeprefix("region="))

    return regions


def database_regions(conn):

    rows = conn.execute(
        "SHOW REGIONS FROM DATABASE ti4601"
    ).fetchall()

    regions = set()

    for row in rows:
        regions.add(str(row[1]))

    return regions


def table_is_global(conn, table):

    row = conn.execute(
        f"SHOW CREATE TABLE {table}"
    ).fetchone()

    if row is None:
        return False

    create_sql = str(row[1]).upper()

    return "LOCALITY GLOBAL" in create_sql


def table_is_regional_by_row(conn, table):

    row = conn.execute(
        f"SHOW CREATE TABLE {table}"
    ).fetchone()

    if row is None:
        return False

    create_sql = str(row[1]).upper()

    return "REGIONAL BY ROW" in create_sql


def check(label, function, hint):

    try:

        result = function()

    except psycopg.Error as error:

        print(f"[FAIL] {label}")
        print(f"       Error: {str(error).splitlines()[0]}")
        print(f"       Pista: {hint}")

        return False

    if result:

        print(f"[ OK ] {label}")

        return True

    print(f"[FAIL] {label}")
    print(f"       Pista: {hint}")

    return False


def main():

    try:

        conn = psycopg.connect(
            autocommit=True
        )

    except psycopg.Error as error:

        print("[FAIL] conexión al cluster")
        print(f"       Error: {str(error).splitlines()[0]}")
        print("       Pista: levante los tres nodos primero.")

        return 1

    with conn:

        results = [

            check(
                "tres nodos y localidades activos",
                lambda: EXPECTED_REGIONS <= live_regions(conn),
                "revise las localities de crdb-1, crdb-2 y crdb-3",
            ),

            check(
                "tres regiones configuradas en ti4601",
                lambda: EXPECTED_REGIONS <= database_regions(conn),
                "ejecute proyecto1/configure.sql",
            ),

            check(
                "producto es GLOBAL",
                lambda: table_is_global(conn, "producto"),
                "revise producto en proyecto1/schema.sql",
            ),

            check(
                "stock es REGIONAL BY ROW",
                lambda: table_is_regional_by_row(conn, "stock"),
                "revise stock en proyecto1/schema.sql",
            ),

            check(
                "pedido es REGIONAL BY ROW",
                lambda: table_is_regional_by_row(conn, "pedido"),
                "revise pedido en proyecto1/schema.sql",
            ),

            check(
                "detalle_pedido es REGIONAL BY ROW",
                lambda: table_is_regional_by_row(
                    conn,
                    "detalle_pedido",
                ),
                "revise detalle_pedido en proyecto1/schema.sql",
            ),
        ]

    passed = sum(results)

    print()
    print(
        f"Resultado: {passed}/{len(results)} verificaciones."
    )

    if passed != len(results):

        print(
            "La configuración del proyecto todavía "
            "tiene verificaciones pendientes."
        )

        return 1

    print(
        "Configuración básica del Proyecto 1 correcta."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())