#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from test import run

input = """\
block:
	if exists rrd t:
		log DEBUG No1
	else:
		log DEBUG Yes
rrd "/tmp/rrdtest.rrd" test t
block:
	if exists rrd t:
		log DEBUG Yes
	else:
		log DEBUG No2
list rrd
list rrd t
set rrd 10 t
wait for 0.5
set rrd 11 t
wait for 0.5
set rrd 12 t
list rrd t
block:
	var rrd x last_ds t
	trigger last $x
del rrd t
block:
	if exists rrd t:
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

