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

log = run_logger("ifelse",dot=False).log

input = StringIO("""\
block:
	if true:
		log DEBUG Yes
	else:
		log DEBUG No1
	if true:
		log DEBUG Yes
	else if true:
		log DEBUG No2
	if true:
		log DEBUG Yes
	else if true:
		log DEBUG No3
	else:
		log DEBUG No4
	if true:
		log DEBUG Yes
	else if false:
		log DEBUG No5
	else:
		log DEBUG No6

block:
	if false:
		log DEBUG No7
	else:
		log DEBUG Yes
	if false:
		log DEBUG No8
	else if true:
		log DEBUG Yes
	if false:
		log DEBUG No9
	else if false:
		log DEBUG No10
	else:
		log DEBUG Yes

shutdown
""")

h.main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("ifelse")
load_module("bool")
load_module("block")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

