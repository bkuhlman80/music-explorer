# Music Explorer Makefile

# --- env ---
ifneq (,$(wildcard env/.env))
include env/.env
export
endif
PY := python3
VENV := .venv
ACT := source $(VENV)/bin/activate

.PHONY: all setup freeze pull clean build lint fmt test figures report run deploy clobber reset dictionary dictionary-enrich restart ci
all: setup build test

# --- environment ---
setup:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(ACT) && $(PY) -m pip install --upgrade pip
	@$(ACT) && $(PY) -m pip install -r env/requirements.txt
	@echo "OK"

freeze:
	@$(ACT) && pip freeze > env/requirements.txt

# --- data pipeline ---
# make pull ARTIST="Radiohead"  # else uses ARTISTS_SEED from .env
pull:
	@mkdir -p data/raw
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.pull_sample \
		--base-url "$(MB_BASE_URL)" \
		--user-agent '$(USER_AGENT)' \
		--rate-limit-ms $(MB_RATE_LIMIT_MS) \
		--seed "$(if $(ARTIST),$(ARTIST),$(ARTISTS_SEED))" \
		--outdir data/raw


clean:
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.clean

build:
	@$(ACT) && PYTHONPATH=$(PWD) $(PY) -m app.pipeline.build

dictionary:
	@$(ACT) && $(PY) app/tools/emit_dictionary.py --indir data/raw --out DATA_DICTIONARY.csv

dictionary-enrich:
	@$(ACT) && $(PY) app/tools/enrich_dictionary.py --infile DATA_DICTIONARY.csv --outfile DATA_DICTIONARY_enriched.csv

# --- quality ---
lint:
	@$(ACT) && ruff check app tests
	@$(ACT) && black --check app tests

fmt:
	@$(ACT) && black app tests

test:
	@$(ACT) && pytest -q

# --- artifacts ---
figures:
	@$(ACT) && $(PY) app/figures/export.py

report:
	@$(ACT) && $(PY) app/report/build.py

# --- app ---
run:
	@$(ACT) && streamlit run app/Main.py --server.port $(STREAMLIT_PORT)

restart:
	@pkill -f "streamlit run" || true
	@$(ACT) && streamlit run app/Main.py --server.port $(STREAMLIT_PORT)

# --- CI bundle ---
ci: setup lint clean build test report

# --- housekeeping ---
clobber:
	@rm -rf data/clean/* data/marts/* docs/figures/* docs/report.pdf

reset: clobber
	@rm -rf data/raw/*
