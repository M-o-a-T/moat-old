#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import Load,Unload
from test import run

input = """\
load example
del load example
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.main_words.register_statement(Unload)

run("modules",input)

