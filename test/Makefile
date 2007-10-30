#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)/..
export HOMEVENT_TEST=1

test:
	@set -e; \
	rm -rf real; mkdir real; \
	for f in $(wildcard *.py) ; do \
		echo $$f ...; \
		python $$f; \
	done; \
	if ! diff -ru expect real >/tmp/diff.$$$$ ; then less /tmp/diff.$$$$; \
		rm /tmp/diff.$$$$; exit 1; else rm /tmp/diff.$$$$; exit 0; fi
diff:
	@-diff -ru expect real | less
