#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
import homevent.interpreter as hi
from homevent.context import Context
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.handler import load as ht_load
from StringIO import StringIO
from test import run_logger, logger,logwrite

log = run_logger("logging",dot=False).log

input = StringIO("""\
log DEBUG
log TRACE "This is not logged"
log DEBUG "This is logged"
log WARN "This is logged too"
log
log PANIC
log WARN "This is not logged either"
""")

hi.main_words.register_statement(ShutdownHandler)
ht_load()
load_module("logging")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

