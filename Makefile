PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin
PY := $(BIN)/python
PIP := $(BIN)/pip
STAMP := $(VENV)/.requirements-installed
PROFILE ?= small
MONTHS ?=
ROWS_PER_MONTH ?=
DATA_ARGS := --profile $(PROFILE) $(if $(MONTHS),--months $(MONTHS),) $(if $(ROWS_PER_MONTH),--rows-per-month $(ROWS_PER_MONTH),)

.PHONY: help setup check-duckdb data data-small data-medium data-large parquet demo demo-small demo-medium demo-large sql sizes verify clean clean-venv clean-all

help:
	@echo "DuckDB + Parquet demo targets"
	@echo ""
	@echo "  make setup       Create .venv and install Python dependencies"
	@echo "  make data        Generate sample CSV invoice data; accepts PROFILE, MONTHS, ROWS_PER_MONTH"
	@echo "  make data-small  Generate 3 tiny monthly CSV files"
	@echo "  make data-medium Generate 6 monthly CSV files with 10,000 rows each"
	@echo "  make data-large  Generate 12 monthly CSV files with 100,000 rows each"
	@echo "  make parquet     Convert raw invoice files to partitioned Parquet"
	@echo "  make demo        Run the Python DuckDB demo"
	@echo "  make demo-medium Generate, convert, query, and compare the medium dataset"
	@echo "  make demo-large  Generate, convert, query, and compare the large dataset"
	@echo "  make sql         Run queries.sql with the DuckDB CLI"
	@echo "  make sizes       Compare CSV and Parquet storage"
	@echo "  make verify      Compile scripts and run the full demo flow"
	@echo "  make clean       Remove generated data"
	@echo "  make clean-venv  Remove the Python virtual environment"
	@echo "  make clean-all   Remove generated data and the virtual environment"

setup: $(STAMP)

check-duckdb:
	@command -v duckdb >/dev/null || (echo "DuckDB CLI not found. Install it with: brew install duckdb" && exit 1)

$(VENV):
	$(PYTHON) -m venv $(VENV)

$(STAMP): requirements.txt | $(VENV)
	$(PIP) install -r requirements.txt
	@touch $(STAMP)

data:
	$(PYTHON) generate_sample_data.py $(DATA_ARGS)

data-small:
	$(MAKE) clean
	$(MAKE) data PROFILE=small

data-medium:
	$(MAKE) clean
	$(MAKE) data PROFILE=medium

data-large:
	$(MAKE) clean
	$(MAKE) data PROFILE=large

parquet: setup data
	$(PY) build_parquet.py

demo: clean setup data
	$(PY) build_parquet.py
	$(PY) demo.py

demo-small: data-small setup
	$(PY) build_parquet.py
	$(PY) demo.py
	$(PY) compare_storage.py

demo-medium: data-medium setup
	$(PY) build_parquet.py
	$(PY) demo.py
	$(PY) compare_storage.py

demo-large: data-large setup
	$(PY) build_parquet.py
	$(PY) demo.py
	$(PY) compare_storage.py

sql: check-duckdb parquet
	duckdb -c ".read queries.sql"

sizes: setup
	$(PY) compare_storage.py

verify: setup
	$(PY) -m py_compile generate_sample_data.py build_parquet.py demo.py compare_storage.py
	$(PYTHON) generate_sample_data.py --profile small
	$(PY) build_parquet.py
	$(PY) demo.py
	$(PY) compare_storage.py

clean:
	rm -rf data/raw data/parquet demo.duckdb

clean-venv:
	rm -rf $(VENV)

clean-all: clean clean-venv
