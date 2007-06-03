#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.statement import DoNothingHandler, main_words

from test import run

input = """\
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
	block:
		sync trigger $1
list on
list on "not executed"
sync trigger bar foo
del on "Skip Next"
sync trigger bar foo
del on 1
list on
shutdown
"""

main_words.register_statement(DoNothingHandler)
main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("trigger")
load_module("on_event")

run("on",input)

