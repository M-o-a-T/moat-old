#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
async:
	wait for 10:
		name Foo Bar
	trigger FooBar
wait for 0.2:
	name X1
list wait
list wait Foo Bar
wait for 0.1:
	name Foo Bar
	update
block:
	if exists wait Foo Baz:
		log DEBUG No2
	else:
		log DEBUG Yes
wait for 0.2:
	name X2
trigger DoNow
wait for 0.1:
	name X3
async:
	wait until 8 min:
		name Foo Baz
	trigger Heya
wait for 0.1
block:
	if exists wait Foo Baz:
		log DEBUG Yes
	else:
		log DEBUG No1
on whatever:
	var wait x Foo Baz
	log TRACE We wait $x
sync trigger whatever
wait for 0.3
del wait Foo Baz
block:
	if exists wait Foo Baz:
		log DEBUG No3
	else:
		log DEBUG Yes
wait for 0.2
# observe no HeYa event
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")
load_module("logging")
load_module("ifelse")
load_module("on_event")

run("wait",input)

