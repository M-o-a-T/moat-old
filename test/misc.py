#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
trigger foo1
trigger bar1
wait for 0.1
sync trigger foo2
sync trigger bar2
wait for 0.1
skip this:
	trigger never the same
block:
	trigger foo3
	trigger bar3
wait for 0.1
block:
	if exists file "misc2":
		include "misc2"
	else:
		include "test/misc2"
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")
load_module("file")
load_module("ifelse")

run("misc",input)

