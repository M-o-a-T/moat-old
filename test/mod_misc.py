#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
trigger foo1
trigger bar1
wait A: for 0.1
trigger foo2 :sync
trigger bar2 :sync
wait B: for 0.1
skip this:
	trigger never the same
block:
	trigger foo3
	trigger bar3
wait C: for 0.1
block:
	if exists file "misc2":
		include "misc2"
	else:
		include "test/misc2"
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("block")
load_module("path")
load_module("file")
load_module("ifelse")

run("misc",input)

