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
from homevent.module import load_module,Load,ModuleExists
from homevent.statement import DoNothingHandler
from test import run

input = """\
if not exists module bool: load bool
if not exists module logging: load logging
if not exists module block: load block
if not exists module trigger: load trigger
if not exists module wait: load wait
if not exists module on_event: load on_event
if not exists module wago: load wago
log DEBUG

async:
	connect wago localhost 59069:
		name test
		#ping 1

#wago input foo bar:
#	port 1 1
#
#wago output some where:
#	port 2 1
#
#wago counter baz:
#	port 1 2
#
#
#set wago on some where
#block:
#	var wago port some where
#	log DEBUG portstate $port
#
#set wago off some where :for 2
wait:
	for 0.5
	debug force
	
list
list wago conn
list wago conn test
list wago server
list wago server test
block:
	if exists wago test:
		log DEBUG Yes
	else:
		log DEBUG No1
	if connected wago test:
		log DEBUG Yes
	else:
		log DEBUG No2
	if exists wago test stupid:
		log DEBUG No3
	else:
		log DEBUG Yes

shutdown
"""

h.main_words.register_statement(DoNothingHandler)
h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

load_module("block")
load_module("file")
load_module("ifelse")
load_module("path")
load_module("data")

run("wago",input)

