#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
block:
	if exists state foo bar:
		log TRACE "No‽"
	else:
		log TRACE "Yes!"
log TRACE Set to ONE
set state one foo bar
log TRACE Set to TWO
set state two foo bar
on state * three foo bar:
	log TRACE Set to FOUR
	set state four foo bar
async:
	log TRACE Set to THREE
	set state three foo bar
wait for 0.1
list state
list state foo bar
block:
	if state three foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽"
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽"
block:
	if last state two foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽"
on whatever:
	var state x foo bar
	log TRACE We got $x
sync trigger whatever
del state foo bar
list state
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("state")
load_module("block")
load_module("wait")
load_module("on_event")
load_module("logging")
load_module("ifelse")
load_module("trigger")

run("state",input)

