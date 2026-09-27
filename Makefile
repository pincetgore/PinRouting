.PHONY: all lint test build help

PYTHON ?= python3
PYTHONPATH := tools

help:
	@echo "PinRouting Developer Commands:"
	@echo "  make lint    - Lint routing profiles and geosite definitions"
	@echo "  make test    - Run regression routing test suite"
	@echo "  make build   - Build HAPP, INCY, and SHADOWROCKET configurations"
	@echo "  make all     - Lint, test, and build"

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting lint

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting test

build:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting build

all: lint test build
