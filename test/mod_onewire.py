#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from test import run

input = """\
block:
	if exists file "onewire2":
		include "onewire2"
	else:
		include "test/onewire2"
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")

run("onewire",input)

