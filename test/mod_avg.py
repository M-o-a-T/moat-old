#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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
#log TRACE
list avg
avg test
list avg
list avg test
wait: for 0.2
set avg 2 test
list avg test
wait: for 1
list avg test
set avg 5 test
list avg test
block:
	if exists avg test:
		log DEBUG Yes
	else:
		log DEBUG No0
block:
	var avg X test
	if equal $X 2:
		log DEBUG Yes
	else:
		log DEBUG No1

wait: for 2
block:
	var avg X test
	if equal $X 4:
		log DEBUG Yes
	else:
		log DEBUG No2

del avg test
block:
	if exists avg test:
		log DEBUG No3
	else:
		log DEBUG Yes
list avg
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("avg")
load_module("block")
load_module("data")
load_module("logging")
load_module("wait")
load_module("tests")
load_module("ifelse")
load_module("bool")
load_module("on_event")

run("avg",input)

