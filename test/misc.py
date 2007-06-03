#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
trigger foo1
trigger bar1
wait 0.1
sync trigger foo2
sync trigger bar2
wait 0.1
skip this:
	trigger never the same
block:
	trigger foo3
	trigger bar3
wait 0.1
block:
	sync trigger foo4
	block:
		sync trigger bar4
async:
	wait 0.1
	trigger foo5
wait 0.2
trigger bar5
wait 0.1
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")

run("misc",input)

