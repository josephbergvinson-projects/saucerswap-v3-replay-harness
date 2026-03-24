PYTHON ?= python3
NODE ?= /opt/homebrew/bin/node
PACKAGE := saucerswap_v3_replay

.PHONY: help validate-config test compile layout export-metabase normalize-event-level

help:
	@echo "Targets: validate-config test compile layout export-metabase normalize-event-level"

validate-config:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE).cli validate-config

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

compile:
	$(PYTHON) -m compileall src

layout:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE).cli layout

normalize-event-level:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE).cli normalize-event-level

export-metabase:
	$(NODE) scripts/export_metabase_csv.js
