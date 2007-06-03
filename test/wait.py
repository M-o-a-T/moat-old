#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
async:
	wait 10:
		name Foo Bar
	trigger FooBar
wait 0.2:
	name Foo Bar
	update
block:
	if exists wait Foo Baz:
		log DEBUG No2
	else:
		log DEBUG Yes
wait 0.1
trigger DoNow
wait 0.1
async:
	wait 0.7:
		name Foo Baz
	trigger Heya
wait 0.1
block:
	if exists wait Foo Baz:
		log DEBUG Yes
	else:
		log DEBUG No1
wait 0.3
del wait Foo Baz
block:
	if exists wait Foo Baz:
		log DEBUG No3
	else:
		log DEBUG Yes
wait 0.2
# observe no HeYa event
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")
load_module("logging")
load_module("ifelse")

run("wait",input)

