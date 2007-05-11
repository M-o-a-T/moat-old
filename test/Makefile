#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)/..
export HOMEVENT_TEST=1

test:
	@set -e; \
	for f in $(wildcard *.py) ; do \
		echo $$f ...; \
		python $$f; \
	done; \
	echo All tests OK.
