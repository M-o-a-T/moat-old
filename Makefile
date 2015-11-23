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

export PYTHONPATH?=$(shell pwd)
DESTDIR ?= "/"
PYDESTDIR ?= ${DESTDIR}
PYTHON ?= python3

all: subfiles
	cp -a _geventreactor/Pinako/geventrpyc/__init__.py moat/gevent_rpyc.py
	$(MAKE) -C fs20 all
	$(MAKE) -C wago all
	$(PYTHON) setup.py build
install: installsub
	$(PYTHON) setup.py install --root="$(PYDESTDIR)" --no-compile -O0 --install-layout=deb
installsub:
	$(MAKE) -C fs20 install ROOT=$(DESTDIR)
	$(MAKE) -C wago install ROOT=$(DESTDIR)

subfiles: moat/gevent_rpyc.py

moat/gevent_rpyc.py: _geventreactor/Pinako/geventrpyc/__init__.py
	cp -a _geventreactor/Pinako/geventrpyc/__init__.py moat/gevent_rpyc.py

_geventreactor/Pinako/geventrpyc/__init__.py: submod
submod:
	if test ! -e _geventreactor/.git ; then \
	git submodule init; \
	git submodule update; \
	fi
FIX:
	@if test ! -d moat/modules; then ln -s ../modules moat/modules; fi

clean:
	$(PYTHON) setup.py clean --build-base="$(PYDESTDIR)"
	rm -rf build
	@$(MAKE) -C fs20 --no-print-directory clean
	@$(MAKE) -C wago --no-print-directory clean


test: all
	@rm -f test.log
	py.test-3 --cov-report term-missing \
		--assert=plain tests \
		--cov=tests \
		--cov=moat.cmd \
		--cov=moat.proto \
		--cov=moat.script \
		--cov-config .coveragerc

otest: all
	@$(MAKE) -C test --no-print-directory otest
diff: FIX
	@$(MAKE) -C test --no-print-directory diff

ow: FIX
	sh test/interactive/onewire.sh
a amqp: FIX
	$(PYTHON) test/interactive/main.py test/interactive/amqp
w wago: FIX
	$(PYTHON) test/interactive/main.py test/interactive/wago
op onewire_poll: FIX
	$(PYTHON) scripts/daemon.py test/interactive/onewire_poll
of onewire_fake: FIX
	env MOAT_TEST=1 $(PYTHON) scripts/daemon.py test/interactive/onewire_fake
om onewire_moat: FIX
	env MOAT_TEST=1 $(PYTHON) scripts/daemon.py test/interactive/onewire_moat
wd wagodebug: FIX
	pdb test/interactive/main.py test/interactive/wago
f fs20: FIX
	$(PYTHON) test/interactive/main.py test/interactive/fs20
fd fs20debug: FIX
	pdb test/interactive/main.py test/interactive/fs20
i interactive: FIX
	env LIBEV_FLAGS=1 MOAT_TEST=1 $(PYTHON) test/interactive/main.py
id interactivedebug d debug: FIX
	pdb test/interactive/main.py
r run: FIX
	$(PYTHON) scripts/daemon.py -t DEBUG examples/smurf.he
tr trace: FIX
	$(PYTHON) scripts/daemon.py -t TRACE examples/smurf.he
sr ssh:
	$(PYTHON) scripts/daemon.py -t TRACE examples/ssh.he

lab:
	## private
	set -e; \
	F="../moat_$$(dpkg-parsechangelog | sed -ne 's/^Version:[[:space:]]//p')_i386.changes"; \
	echo "$$F" /daten/debian/pool/main/h/moat/"$$(basename "$$F")"; \
	test ! -f "$$F"; \
	sudo chroot /daten/chroot/i386/wheezy sudo -u smurf make -C $(PWD) lab_ || test -s "$$F"; \
	dput -u smurf "$$F"; \
	echo -n "Waiting for archive "; while test ! -f "/daten/debian/pool/main/h/moat/$$(basename "$$F")" ; do echo -n "."; sleep 1;done;echo " done."
	make clean
	ssh -lroot lab apt-get update
	ssh -lroot lab apt-get install -y moat=$$(dpkg-parsechangelog | sed -ne 's/^Version:[[:space:]]//p')
lab_:
	debuild -b

schema:
	$(PYTHON) irrigation/manage.py schemamigration --auto rainman
	find irrigation/rainman/migrations/ -name \*.py -mtime -0.1 -print0 | xargs -0r \
	sed -i \
		-e "s/{'default': 'datetime.datetime(.* tzinfo=<UTC>)'}/{}/" \
		-e "s/'default': 'datetime.datetime(.* tzinfo=<UTC>)',//"    \
		-e "s/(default=datetime.datetime(.*tzinfo=<UTC>))/()/"       \
		-e "s/default=datetime.datetime(.*tzinfo=<UTC>),//"
	$(PYTHON) irrigation/manage.py migrate rainman
	# might have to modify if broken
	git add irrigation/rainman/migrations/*.py


.PHONY: FIX test i interactive submod
