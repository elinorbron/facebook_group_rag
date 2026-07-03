.PHONY: install ingest run test clean

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON := $(ROOT).venv/bin/python
STREAMLIT := $(ROOT).venv/bin/streamlit

install:
	cd $(ROOT) && ./setup.sh

ingest:
	cd $(ROOT) && ANONYMIZED_TELEMETRY=False PYTHONPATH=$(ROOT) $(PYTHON) -m src.ingest

run:
	cd $(ROOT) && ANONYMIZED_TELEMETRY=False PYTHONPATH=$(ROOT) $(STREAMLIT) run src/app.py

test:
	cd $(ROOT) && PYTHONPATH=$(ROOT) $(PYTHON) -m pytest tests/ -q

clean:
	rm -rf $(ROOT)index/*
