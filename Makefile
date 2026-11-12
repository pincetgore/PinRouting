.PHONY: all lint test build check-dead help

PYTHON ?= python3
PYTHONPATH := tools

help:
	@echo "PinRouting Developer Commands:"
	@echo "  make lint       - Lint routing profiles and geosite definitions"
	@echo "  make test       - Run regression routing test suite"
	@echo "  make build      - Build HAPP, INCY, and SHADOWROCKET configurations"
	@echo "  make check-dead - Check for dead domains (dry-run)"
	@echo "  make all        - Lint, build, and test"

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting lint

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting test

build:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting build

check-dead:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pinrouting check-dead

# build before test: the tests read the generated configs
all: lint build test
