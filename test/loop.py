#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
async:
	wait for 1.9:
		name Foo Bar
wait for 0.1
block:
	log DEBUG Start
	while exists wait Foo Bar:
		log DEBUG waiting
		wait for 0.7
		log DEBUG testing
	log DEBUG Done

shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("loop")
load_module("wait")
load_module("block")
load_module("logging")

run("loop",input)

