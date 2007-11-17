#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from test import run

input = """\
connect net foo localhost 50333
wait for 1
list net
list net foo
send net foo "bar"
wait for 1.1
disconnect net foo
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("wait")
load_module("net")

run("net",input)

