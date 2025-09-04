-include .env
-include env/.env
export

PY := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
ACT := . $(VENV)/bin/activate

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:

# Defaults if not provided
MB_BASE_URL      ?= https://musicbrainz.org/ws/2
MB_RATE_LIMIT_MS ?= 1100
MB_MAX_RETRIES   ?= 3
MB_TIMEOUT_S     ?= 30
TZ               ?= UTC
ARTISTS_SEED     ?= Radiohead,Daft Punk,Beyonce
STREAMLIT_PORT   ?= 8501
STREAMLIT_BROWSER_GATHER_USAGE_STATS ?= false

.PHONY: all env-check setup freeze lock lock-upgrade pull pull_recordings clean build guard_raw guard_clean lint fmt test figures report run deploy clobber reset dictionary dictionary-enrich profile-dict restart ci release-pr version

env-check:
	@test -n "$(USER_AGENT)" || (echo "ERROR: Set USER_AGENT in .env as 'app/version (email)'"; exit 1)

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
	@set -a; [ -f .env ] && . ./.env; set +a; \
	$(VENV_BIN)/python -m app.pipeline.pull_recordings \
	  --base-url "$${MB_BASE_URL:-https://musicbrainz.org/ws/2}" \
	  --user-agent "$${USER_AGENT:?Set USER_AGENT in .env as 'app/version (email)'}" \
	  --seed "$${ARTISTS_SEED:-Radiohead,Daft Punk,Beyonce}" \
	  --rate-limit-ms "$${MB_RATE_LIMIT_MS:-1100}" \
	  --timeout-s "$${MB_TIMEOUT_S:-30}" \
	  --retries "$${MB_MAX_RETRIES:-3}" \
	  --out "data/raw/recordings.jsonl"

clean:
	$(VENV_BIN)/python -m app.pipeline.clean

guard_raw:
	@test -s data/raw/recordings.jsonl || $(MAKE) pull

guard_clean: guard_raw
	@test -f data/clean/release_groups.parquet || $(VENV_BIN)/python -m app.pipeline.clean

build: guard_clean
	$(VENV_BIN)/python -m app.pipeline.build

report:
	$(VENV_BIN)/python -m app.report.build

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
	$(VENV_BIN)/python -m app.figures.export

restart:
	@pkill -f "streamlit run" || true
	@$(ACT) && streamlit run -m app.streamlit_app --server.port $(STREAMLIT_PORT)

	
ci: setup lint clean build figures test report profile-dict

clobber:
	@rm -rf data/clean/* data/marts/* docs/figures/* docs/report.pdf

reset: clobber
	@rm -rf data/raw/*

release-pr:
	@echo "Triggering release-please via workflow_dispatch (or push to main)."

version:
	@cat VERSION
