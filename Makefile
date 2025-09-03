ifneq (,$(wildcard env/.env))
include env/.env
export
endif
PY := python3
VENV := .venv
ACT := . $(VENV)/bin/activate
SHELL := /usr/bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:


.PHONY: all setup freeze lock lock-upgrade pull pull_recordings 
	clean build lint fmt test figures report run deploy clobber reset 
	dictionary dictionary-enrich profile-dict restart ci

setup:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(ACT) && $(PY) -m pip install --upgrade pip pip-tools
	@$(ACT) && pip-sync env/requirements.txt env/requirements-dev.txt
	@echo "OK"

freeze:
	@echo "Use 'make lock' or 'make lock-upgrade' instead."

lock:
	@$(ACT) && pip-compile --generate-hashes env/requirements.in  -o env/requirements.txt
	@$(ACT) && pip-compile -c env/requirements.txt --generate-hashes env/dev.in -o env/requirements-dev.txt

lock-upgrade:
	@$(ACT) && pip-compile --upgrade --generate-hashes env/requirements.in  -o env/requirements.txt
	@$(ACT) && pip-compile -c env/requirements.txt --upgrade --generate-hashes env/dev.in -o env/requirements-dev.txt

pull: pull_recordings

pull_recordings:
	. .venv/bin/activate && python -m app.pipeline.pull_recordings \
	  --base-url "$(MB_BASE_URL)" \
	  --user-agent "$(USER_AGENT)" \
	  --seed "$(ARTISTS_SEED)" \
	  --rate-limit-ms "$(MB_RATE_LIMIT_MS)" \
	  --timeout-s "$(MB_TIMEOUT_S)" \
	  --retries "$(MB_MAX_RETRIES)" \
	  --out "data/raw/recordings.jsonl"

clean:
	. .venv/bin/activate && python -m app.pipeline.clean
build:
	. .venv/bin/activate && python -m app.pipeline.build

report:
	. .venv/bin/activate && python -m app.report.build

run:
	STREAMLIT_BROWSER_GATHER_USAGE_STATS=$(STREAMLIT_BROWSER_GATHER_USAGE_STATS) \
	STREAMLIT_SERVER_PORT=$(STREAMLIT_PORT) \
	. .venv/bin/activate && streamlit run app/Main.py

dictionary:
	@$(ACT) && $(PY) -m app.tools.emit_dictionary --indir data/raw --out DATA_DICTIONARY.csv

profile-dict:
	@$(ACT) && $(PY) -m app.tools.profile_dictionary --out docs/DATA_DICTIONARY_profile.csv

lint:
	@$(ACT) && ruff check app tests
	@$(ACT) && black --check app tests

fmt:
	@$(ACT) && black app tests

test: figures
	@$(ACT) && PYTHONPATH=. pytest -q

figures:
	@$(ACT) && $(PY) -m app.figures.export

restart:
	@pkill -f "streamlit run" || true
	@$(ACT) && streamlit run -m app.streamlit_app --server.port $(STREAMLIT_PORT)

	
ci: setup lint clean build figures test report profile-dict

clobber:
	@rm -rf data/clean/* data/marts/* docs/figures/* docs/report.pdf

reset: clobber
	@rm -rf data/raw/*
