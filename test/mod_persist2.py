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
	if exists state foo bar:
		log TRACE "No‽ 1"
	else:
		log TRACE "Yes!"
	if saved state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 3"
state foo bar:
	saved
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 2"
	if saved state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 4"

block:
	var state x foo bar
	log TRACE We still have $x
del state foo bar
list state
block:
	if saved state foo bar:
		log TRACE "No‽ 9"
	else:
		log TRACE "Yes!"
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("state")
load_module("block")
load_module("data")
load_module("on_event")
load_module("logging")
load_module("ifelse")
load_module("trigger")

run("persist2",input)

