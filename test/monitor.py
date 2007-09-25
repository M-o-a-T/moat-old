#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
log TRACE
on monitor value *VAL foo bar:
	var monitor OLDVAL foo bar
	if null $OLDVAL:
		log TRACE First value is $VAL
	else:
		log TRACE Go from $OLDVAL to $VAL
monitor test 0 100 2:
	name foo bar
	delay for 0.4
wait for 1
list monitor
list monitor foo bar
wait for 0.8
del monitor foo bar
list monitor
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("monitor")
load_module("block")
load_module("logging")
load_module("wait")
load_module("tests")
load_module("ifelse")
load_module("bool")
load_module("on_event")

run("monitor",input)

