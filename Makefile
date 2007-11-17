#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)
DESTDIR ?= "/"

all:
	@echo Nothing to do.
install:
	python setup.py --root=$(DESTDIR)

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
	python daemon.py -t DEBUG smurf.ow
tr trace:
	python daemon.py -t TRACE smurf.ow

.PHONY: test i interactive
