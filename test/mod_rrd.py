#!/usr/bin/python
# -*- coding: utf-8 -*-

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
wait for 1.1
set rrd 10 t tt ttt
wait for 1.1
set rrd 11 t tt ttt
wait for 1.1
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
load_module("rrd")
load_module("logging")
load_module("block")
load_module("wait")

run("rrd",input)

