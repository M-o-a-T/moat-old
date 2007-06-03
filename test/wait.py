#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
async:
	wait 10:
		name FooBar
	trigger FooBar
wait 0.2:
	name FooBar
	update
wait 0.1
trigger DoNow
wait 0.1
async:
	wait 0.7:
		name FooBaz
	trigger Heya
wait 0.4
del wait FooBaz
wait 0.2
# observe no HeYa event
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")

run("wait",input)

