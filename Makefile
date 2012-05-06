#!/usr/bin/make -f
##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

all:
	cp -a _geventreactor/Pinako/geventreactor/__init__.py homevent/geventreactor.py
	#cp -a _zeromq/gevent_zeromq/core.py homevent/zeromq.py
	cp -a _geventreactor/Pinako/geventrpyc/__init__.py homevent/gevent_rpyc.py
	$(MAKE) -C fs20 all
	$(MAKE) -C wago all
	python setup.py build
install:
	$(MAKE) -C fs20 install ROOT=$(DESTDIR)
	$(MAKE) -C wago install ROOT=$(DESTDIR)
	python setup.py install --root="$(DESTDIR)" --no-compile -O0 --install-layout=deb

FIX:
	@if test ! -d homevent/modules; then ln -s ../modules homevent/modules; fi

clean:
	python setup.py clean --build-base="$(DESTDIR)"
	rm -rf build
	@$(MAKE) -C fs20 --no-print-directory clean
	@$(MAKE) -C wago --no-print-directory clean


test: FIX
	@$(MAKE) -C test --no-print-directory test
diff: FIX
	@$(MAKE) -C test --no-print-directory diff

ow: FIX
	sh test/interactive/onewire.sh
w fs20: FIX
	python test/interactive/main.py test/interactive/wago
wd wagodebug: FIX
	pdb test/interactive/main.py test/interactive/wago
f fs20: FIX
	python test/interactive/main.py test/interactive/fs20
fd fs20debug: FIX
	pdb test/interactive/main.py test/interactive/fs20
i interactive: FIX
	env HOMEVENT_TEST=1 python test/interactive/main.py
id interactivedebug d debug: FIX
	pdb test/interactive/main.py
r run: FIX
	python scripts/daemon.py -t DEBUG examples/smurf.he
tr trace: FIX
	python scripts/daemon.py -t TRACE examples/smurf.he
sr ssh:
	python scripts/daemon.py -t TRACE examples/ssh.he

lab:
	## private
	set -e; \
	F="../homevent_$$(dpkg-parsechangelog | sed -ne 's/^Version:[[:space:]]//p')_i386.changes"; \
	test ! -f "$F"; \
	sudo chroot /daten/chroot/i386/wheezy sudo -u smurf make -C $(PWD) lab_ || test -s "$$F"; \
	dput -u smurf "$$F"
	echo -n "Waiting for archive "; while ! -f /daten/debian/pool/main/h/homevent/"$$(basename "$F")" ; do echo -n "."; sleep 1;done;echo ""
	ssh -lroot lab apt-get update
	ssh -lroot lab apt-get install -y homevent=$$(dpkg-parsechangelog | sed -ne 's/^Version:[[:space:]]//p')
lab_:
	debuild -b

schema:
	python irrigation/manage.py schemamigration --auto rainman
	python irrigation/manage.py migrate rainman
	# might have to modify if broken
	git add irrigation/rainman/migrations/*.py


.PHONY: test i interactive
