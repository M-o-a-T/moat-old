#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
import homevent.interpreter as hi
from homevent.context import Context
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.statement import main_words,DoNothingHandler
from StringIO import StringIO
from test import run_logger, logger,logwrite

log = run_logger("on",dot=False).log

input = StringIO("""\
on foo:
	prio 50
	name "Do nothing"
	do nothing
on foo:
	prio 55
	name "Skip Next"
	skip next
	doc "Causes the prio-60 thing to not be executed"
on foo:
	prio 60
	name "not executed"
	sync trigger OuchNo
	doc "Is not executed because of the former 'skip next' (until that's gone)"
on bar *:
	sync trigger foo
list on
list on "not executed"
sync trigger bar baz
drop on "Skip Next"
sync trigger bar baz
drop on 1
list on
shutdown
""")

h.main_words.register_statement(DoNothingHandler)
h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("on_event")

def main():
	d = hp.parse(input, hi.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

