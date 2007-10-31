#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
#log TRACE
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
block:
	if waiting monitor foo bar:
		log DEBUG No0
	else:
		log DEBUG Yes
list monitor
list monitor foo bar
wait for 0.8
del monitor foo bar
list monitor

on monitor checking baz zaz:
	async:
		set monitor 10 baz zaz
		wait for 0.2
		set monitor 13 baz zaz
		wait for 0.2
		set monitor 14 baz zaz
	
monitor passive:
	name baz zaz
	delay for 0.3
	require 2 2
list monitor baz zaz

wait for 0.2
block:
	if waiting monitor baz zaz:
		log DEBUG Yes
	else:
		log DEBUG No1
wait for 0.5
block:
	if waiting monitor baz zaz:
		log DEBUG No2
	else:
		log DEBUG Yes

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

