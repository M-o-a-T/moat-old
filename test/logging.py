#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
log DEBUG
log TRACE "This is not logged"
log DEBUG "This is logged"
log WARN "This is logged too"
log
log PANIC
log WARN "This is not logged either"
"""

h.main_words.register_statement(ShutdownHandler)
load_module("logging")

run("logging",input)
