#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)

all:
	@echo Nothing to do yet.
install:
	@echo Not implemented yet.
test:
	@$(MAKE) -C test --no-print-directory test
diff:
	@$(MAKE) -C test --no-print-directory diff

ow:
	sh test/interactive/onewire.sh
i interactive:
	python test/interactive/main.py
d debug:
	pdb test/interactive/main.py
r run:
	python daemon.py -t TRACE smurf.ow

.PHONY: test i interactive
