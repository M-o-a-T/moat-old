#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2012, Matthias Urlichs <matthias@urlichs.de>
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
input fake :name foo bar
output fake :name foo bar
list input
list input foo bar
list output
list output foo bar

set output TEST foo bar
block:
	var input bla foo bar
	if equal $bla "TEST":
		log DEBUG Yes
	else:
		log DEBUG No $bla

set output GRMPF foo bar
block:
	var input bla foo bar
	if equal $bla "TEST":
		log DEBUG No $bla
	else:
		log DEBUG Yes

list input foo bar
list output foo bar

shutdown
"""

h.main_words.register_statement(ShutdownHandler)
load_module("ifelse")
load_module("data")
load_module("block")
load_module("bool")
load_module("logging")
load_module("tests")

run("io",input)

