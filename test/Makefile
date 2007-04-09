#!/usr/bin/make -f

export PYTHONPATH=$(shell pwd)/..

test:
	@set -e; \
	for f in $(wildcard *.py) ; do \
		echo $$f ...; \
		python $$f; \
	done; \
	echo All tests OK.
