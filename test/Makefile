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

export PYTHONPATH=$(shell pwd)/..:$(shell pwd)/../dabroker:$(shell pwd)/../../smurf/python
export HOMEVENT_TEST=1

test:
	@rm -f /tmp/moat.$$(id -un).db /tmp/moat.db.$$(id -u) 2>/dev/null
	@set -e; \
	rm -rf real; mkdir real; \
	for f in $(wildcard *.sh) ; do \
		echo $$f ...; \
		sh $$f; \
	done; \
	for f in $(wildcard *.py) ; do \
		echo $$f ...; \
		python $$f; \
	done; \
	if ! diff -ru expect real >/tmp/diff.$$$$ ; then less /tmp/diff.$$$$; \
		rm /tmp/diff.$$$$; exit 1; else rm /tmp/diff.$$$$; exit 0; fi
diff:
	@-diff -ru expect real | less
