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

log = run_logger("trigger",dot=False).log

input = StringIO("""\
sync trigger foo
wait 1m -90s 0.5min +.5s
sync trigger bar
shutdown
""")

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

