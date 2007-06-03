#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
import homevent.interpreter as hi
from homevent.context import Context
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from StringIO import StringIO
from test import run_logger, logger,logwrite

log = run_logger("state",dot=False).log

input = StringIO("""\
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
wait 0.1
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
""")

h.main_words.register_statement(ShutdownHandler)
load_module("state")
load_module("block")
load_module("wait")
load_module("on_event")
load_module("logging")
load_module("ifelse")
load_module("trigger")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

