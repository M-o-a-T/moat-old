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
block:
	if exists rrd t tt ttt:
		log DEBUG No1
	else:
		log DEBUG Yes
rrd "/tmp/rrdtest.rrd" test t tt ttt
block:
	if exists rrd t tt ttt:
		log DEBUG Yes
	else:
		log DEBUG No2
list rrd
list rrd t tt ttt
wait: for 1.1
set rrd 10 t tt ttt
wait: for 1.1
set rrd 11 t tt ttt
wait: for 1.1
set rrd 12 t tt ttt
list rrd t tt ttt
block:
	var rrd x last_ds t tt ttt
	trigger last $x
del rrd t tt ttt
block:
	if exists rrd t tt ttt:
		log DEBUG No3
	else:
		log DEBUG Yes

"""

h.main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("ifelse")
load_module("data")
load_module("rrd")
load_module("logging")
load_module("block")
load_module("wait")

run("rrd",input)

