#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load
from homevent.statement import global_words
from test import run

global_words.register_statement(Load)


input = """\
load ssh
block:
	if exists directory "keys":
		ssh directory "keys"
	else:
		ssh directory "../keys"

# TODO: run an external test ‽
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("path")
load_module("ifelse")

run("ssh",input)

