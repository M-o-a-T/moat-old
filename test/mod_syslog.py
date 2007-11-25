#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
wait for 0.2
syslog local1 trace localhost 55514
log DEBUG "One Debug"
del syslog local1 localhost 55514

syslog local5 info localhost 55514
log DEBUG "Five Debug"
log WARN "Five Warn"
del syslog local5 localhost 55514
wait for 0.2
"""

h.main_words.register_statement(ShutdownHandler)
load_module("logging")
load_module("syslog")
load_module("wait")

run("syslog",input)
