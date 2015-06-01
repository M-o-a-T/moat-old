#!/usr/bin/python
# -*- coding: utf-8 -*-
##BP
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

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module
from moat.statement import main_words
from test import run

input = """\
wait startup:
	for 0.2
	debug force
block:
	if exists rrd server t tt ttt:
		log ERROR No1
	else:
		log TRACE Yes
connect rrd localhost 52442 :name t tt ttt
block:
	if exists rrd server t tt ttt:
		log TRACE Yes
	else:
		log ERROR No2
list rrd server
list rrd server t tt ttt
block:
	if exists rrd file a aa aaa:
		log ERROR No1a
	else:
		log TRACE Yes
rrd file "/tmp/rrdtest.rrd" a aa aaa :server t tt ttt
block:
	if exists rrd file a aa aaa:
		log TRACE Yes
	else:
		log ERROR No2a
list rrd file
list rrd file a aa aaa

wait:
	for 0.1
	debug force
set rrd 10 a aa aaa
wait:
	for 0.1
	debug force
set rrd 11 a aa aaa
wait:
	for 0.1
	debug force

block:
	try:
		set rrd 12 a aa aaa
		log ERROR No error
	catch:
		log TRACE Yes error
	
list rrd file a aa aaa
del rrd file a aa aaa
block:
	if exists rrd file a aa aaa:
		log ERROR No3
	else:
		log TRACE Yes
del rrd server t tt ttt
block:
	if exists rrd server t tt ttt:
		log ERROR No4
	else:
		log TRACE Yes
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
load_module("errors")

run("rrdc",input)

