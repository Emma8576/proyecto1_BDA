# Instituto Tecnológico de Costa Rica — TI-4601
# Interfaz operativa genérica (Compose). Smoke tests = documentados en README, no targets.

.PHONY: help up down down-v build shell test-tx lab-concurrency \
	lab1-up lab1-down lab1-down-v lab1-shell lab1-status lab1-check reset-pg \
	p1-chaos-setup p1-chaos-probe p1-chaos-rpo p1-chaos-reset

COMPOSE := docker compose
ISOLATION ?= READ_COMMITTED
WORKERS ?= 40
RETRIES ?= 8

help:
	@echo "TI-4601 · entorno"
	@echo "  make up | down | down-v | build | shell | reset-pg"
	@echo "  make test-tx"
	@echo "  make lab-concurrency ISOLATION=READ_COMMITTED|SERIALIZABLE"
	@echo "  Lab 1: make lab1-up | lab1-status | lab1-shell | lab1-check"
	@echo "         make lab1-down | lab1-down-v"
	@echo "  Configuración, medición y chaos: seguir labs/lab1-cluster/README.md"
	@echo ""
	@echo "Smoke test (manual): ver README.md § Verificar el entorno"
	@echo "Docs: labs/README.md · labs/lab0-concurrency/ · labs/lab1-cluster/"

up:
	$(COMPOSE) up -d postgres

down:
	$(COMPOSE) down --remove-orphans

down-v:
	$(COMPOSE) down -v --remove-orphans

build:
	$(COMPOSE) build app

shell: up
	$(COMPOSE) run --rm app bash

reset-pg: down-v up
	@echo "Volumen recreado; initdb volvió a cargar CSV."

test-tx: up
	$(COMPOSE) run --rm app python3 transactions/read.py
	$(COMPOSE) run --rm app python3 transactions/transform.py
	$(COMPOSE) run --rm app python3 transactions/aggregate.py
	$(COMPOSE) run --rm app python3 transactions/join.py
	$(COMPOSE) run --rm app python3 transactions/answer.py

lab-concurrency: up
	$(COMPOSE) run --rm -e ISOLATION=$(ISOLATION) -e WORKERS=$(WORKERS) -e RETRIES=$(RETRIES) \
		app python3 labs/lab0-concurrency/stress.py --isolation $(ISOLATION) --workers $(WORKERS) --retries $(RETRIES)

lab1-up: build
	$(COMPOSE) --profile lab1 up -d crdb-1 crdb-2 crdb-3
	$(COMPOSE) --profile lab1 up crdb-init

lab1-down:
	$(COMPOSE) --profile lab1 down

lab1-down-v:
	$(COMPOSE) --profile lab1 down -v

lab1-shell:
	$(COMPOSE) --profile lab1 run --rm app-crdb bash

lab1-status:
	$(COMPOSE) --profile lab1 ps
	docker exec ti4601-crdb-1 cockroach node status --insecure

lab1-check:
	$(COMPOSE) --profile lab1 run --rm --no-deps app-crdb \
		python3 labs/lab1-cluster/verify_cluster.py

p1-chaos-setup:
	docker exec -i ti4601-crdb-1 cockroach sql --insecure --database=ti4601 \
		< proyecto1/chaos_probe_setup.sql

p1-chaos-probe:
	$(COMPOSE) --profile lab1 run --rm --no-deps app-crdb \
		python3 -u proyecto1/chaos_probe.py \
			--duration 40 \
			--signal-file evidence/chaos-e4-stop.epoch \
			--csv evidence/chaos-e4.csv \
		| tee evidence/chaos-e4.txt

p1-chaos-rpo:
	$(COMPOSE) --profile lab1 run --rm --no-deps app-crdb \
		psql -X -v ON_ERROR_STOP=1 -c \
		"SELECT id, version, updated_at FROM ti4601.public.stock_probe WHERE id=1;" \
		| tee evidence/chaos-e4-rpo.txt

p1-chaos-reset:
	docker start ti4601-crdb-2 ti4601-crdb-3
	docker exec -it ti4601-crdb-1 cockroach sql --insecure --database=ti4601 --execute="DROP TABLE IF EXISTS stock_probe;"
	rm -f evidence/chaos-e4-stop.epoch \
		evidence/chaos-e4-stop.txt \
		evidence/chaos-e4.txt \
		evidence/chaos-e4.csv \
		evidence/chaos-e4-before.txt \
		evidence/chaos-e4-node-status.txt \
		evidence/chaos-e4-rpo.txt
