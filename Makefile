#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)

all:
	@echo Nothing to do yet.
install:
	@echo Not implemented yet.
test:
	@$(MAKE) -C test --no-print-directory
ow:
	sh test/interactive/onewire.sh
i interactive:
	python test/interactive/main.py
d debug:
	pdb test/interactive/main.py

.PHONY: test i interactive
