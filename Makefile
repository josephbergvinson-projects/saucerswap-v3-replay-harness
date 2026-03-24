PYTHON ?= python3
PACKAGE := saucerswap_v3_replay

.PHONY: help validate-config test compile layout

help:
	@echo "Targets: validate-config test compile layout"

validate-config:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE).cli validate-config

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

compile:
	$(PYTHON) -m compileall src

layout:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE).cli layout
