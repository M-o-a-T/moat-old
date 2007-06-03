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
wait 0.1
trigger DoNow
wait 0.1
async:
	wait 0.7:
		name Foo Baz
	trigger Heya
wait 0.4
del wait Foo Baz
wait 0.2
# observe no HeYa event
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")

run("wait",input)

