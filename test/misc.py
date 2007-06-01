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

log = run_logger("misc",dot=False).log

input = StringIO("""\
trigger foo1
trigger bar1
wait 0.1
sync trigger foo2
sync trigger bar2
wait 0.1
block:
	trigger foo3
	trigger bar3
wait 0.1
block:
	sync trigger foo4
	block:
		sync trigger bar4
wait 0.1
shutdown
""")

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

