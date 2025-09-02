ifneq (,$(wildcard env/.env))
include env/.env
export
endif
PY := python3
VENV := .venv
ACT := . $(VENV)/bin/activate

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
	. .venv/bin/activate && python app/pipeline/pull_recordings.py \
	  --base-url "$(MB_BASE_URL)" \
	  --user-agent "$(USER_AGENT)" \
	  --seed "$(ARTISTS_SEED)" \
	  --rate-limit-ms "$(MB_RATE_LIMIT_MS)" \
	  --timeout-s "$(MB_TIMEOUT_S)" \
	  --retries "$(MB_MAX_RETRIES)" \
	  --out "data/raw/recordings.jsonl"

clean:
	. .venv/bin/activate && python app/pipeline/clean.py

build:
	. .venv/bin/activate && python -m app/pipeline/build.py

report:
	. .venv/bin/activate && python -m app/report/build.py

run:
	STREAMLIT_BROWSER_GATHER_USAGE_STATS=$(STREAMLIT_BROWSER_GATHER_USAGE_STATS) \
	STREAMLIT_SERVER_PORT=$(STREAMLIT_PORT) \
	. .venv/bin/activate && streamlit run app/Main.py

dictionary:
	@$(ACT) && $(PY) app/tools/emit_dictionary.py --indir data/raw --out DATA_DICTIONARY.csv

profile-dict:
	@$(ACT) && $(PY) app/tools/profile_dictionary.py --out docs/DATA_DICTIONARY_profile.csv

lint:
	@$(ACT) && ruff check app tests
	@$(ACT) && black --check app tests

fmt:
	@$(ACT) && black app tests

test: figures
	@$(ACT) && pytest -q

figures:
	@$(ACT) && $(PY) app/figures/export.py

restart:
	@pkill -f "streamlit run" || true
	@$(ACT) && streamlit run app/streamlit_app.py --server.port $(STREAMLIT_PORT)

ci: setup lint clean build figures test report profile-dict

clobber:
	@rm -rf data/clean/* data/marts/* docs/figures/* docs/report.pdf

reset: clobber
	@rm -rf data/raw/*
