#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from homevent.statement import main_words
from test import run


input = """\
block:
	if exists rrd server t tt ttt:
		log DEBUG No1
	else:
		log DEBUG Yes
connect rrd localhost 52442 :name t tt ttt
block:
	if exists rrd server t tt ttt:
		log DEBUG Yes
	else:
		log DEBUG No2
list rrd server
list rrd server t tt ttt
block:
	if exists rrd file a aa aaa:
		log DEBUG No1a
	else:
		log DEBUG Yes
rrd file "/tmp/rrdtest.rrd" a aa aaa :server t tt ttt
block:
	if exists rrd file a aa aaa:
		log DEBUG Yes
	else:
		log DEBUG No2a
list rrd file
list rrd file a aa aaa
wait: for 1.1
set rrd 10 a aa aaa
wait: for 1.1
set rrd 11 a aa aaa
wait: for 1.1
set rrd 12 a aa aaa
list rrd file a aa aaa
del rrd file a aa aaa
block:
	if exists rrd file a aa aaa:
		log DEBUG No3
	else:
		log DEBUG Yes
del rrd server t tt ttt
block:
	if exists rrd server t tt ttt:
		log DEBUG No4
	else:
		log DEBUG Yes
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("ifelse")
load_module("data")
load_module("rrdc")
load_module("logging")
load_module("block")
load_module("wait")

run("rrdc",input)

