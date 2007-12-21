#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)
DESTDIR ?= "/"

FIX:
	@if test ! -d homevent/modules; then ln -s ../modules homevent/modules; fi

all:
	@$(MAKE) -C audio --no-print-directory all
	python2.5 setup.py build --build-base="$(DESTDIR)"
install:
	@$(MAKE) -C audio --no-print-directory install ROOT=$(DESTDIR)
	python2.5 setup.py install --root="$(DESTDIR)" --no-compile -O0

clean:
	python2.5 setup.py clean --build-base="$(DESTDIR)"
	@$(MAKE) -C audio --no-print-directory clean


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
