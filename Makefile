#!/usr/bin/make -f
##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##

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
