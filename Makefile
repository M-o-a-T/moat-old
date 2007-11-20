#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)
DESTDIR ?= "/"

FIX:
	if test ! -d homevent/modules; then ln -s ../modules homevent/modules; fi

all:
	@echo Nothing to do.
install:
	python setup.py --root=$(DESTDIR)

test: FIX
	@$(MAKE) -C test --no-print-directory test
diff: FIX
	@$(MAKE) -C test --no-print-directory diff

ow: FIX
	sh test/interactive/onewire.sh
i interactive: FIX
	python test/interactive/main.py
d debug: FIX
	pdb test/interactive/main.py
r run: FIX
	python scripts/daemon.py -t DEBUG examples/smurf.he
tr trace: FIX
	python scripts/daemon.py -t TRACE examples/smurf.he

.PHONY: test i interactive
