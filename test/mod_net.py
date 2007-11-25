#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from test import run

input = """\
on net connect foo:
	send net foo "bar"
	list net foo
	disconnect net foo
on net connect baz:
	send net baz "quux"
	list net baz
	disconnect net baz
on net disconnect foo:
	log TRACE dis foo
on net disconnect baz:
	log TRACE dis baz
wait for 0.2
listen net baz localhost 50345
connect net foo localhost 50333
wait for 0.8
log TRACE ending
list net
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("wait")
load_module("logging")
load_module("on_event")
load_module("net")

run("net",input)

