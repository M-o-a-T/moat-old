#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
from homevent.context import Context
from homevent.reactor import ShutdownHandler
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.handler import load as ht_load
from StringIO import StringIO
from test import run_logger, logger,logwrite

log = run_logger("on",dot=False).log

input = StringIO("""\
on foo:
	do nothing
on bar *:
	trigger foo
list on
trigger bar baz
#drop on foo
drop on 1
list on
""")

hp.main_words.register_statement(ShutdownHandler)
ht_load()
load_module("events")

def main():
	d = hp.parse(input, hp.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

