ifneq (,$(wildcard env/.env))
include env/.env
export
endif
PY := python3
VENV := .venv
ACT := . $(VENV)/bin/activate

.PHONY: all setup freeze lock lock-upgrade pull clean build lint fmt test figures report run deploy clobber reset dictionary dictionary-enrich profile-dict restart ci

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

pull:
	@mkdir -p data/raw
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.pull_sample \
		--base-url $(MB_BASE_URL) \
		--user-agent $(USER_AGENT) \
		--rate-limit-ms $(MB_RATE_LIMIT_MS) \
		--seed $(ARTISTS_SEED) \
		--outdir data/raw

clean:
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.clean

build:
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.build

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

report:
	@$(ACT) && $(PY) app/report/build.py

run:
	@$(ACT) && streamlit run app/Main.py --server.port $(STREAMLIT_PORT)

restart:
	@pkill -f "streamlit run" || true
	@$(ACT) && streamlit run app/Main.py --server.port $(STREAMLIT_PORT)

ci: setup lint clean build test figures report profile-dict

clobber:
	@rm -rf data/clean/* data/marts/* docs/figures/* docs/report.pdf

reset: clobber
	@rm -rf data/raw/*
