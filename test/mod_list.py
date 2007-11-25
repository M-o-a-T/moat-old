#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
list module
list module on_event
list worker
list event

on foo:
	block:
		wait for 0.3:
			name foo waiter
wait for 0.1
trigger foo
wait for 0.1
list event
list event 4
wait for 0.3

shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")
load_module("list")
load_module("on_event")

run("list",input)

