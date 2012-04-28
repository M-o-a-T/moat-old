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
		log TRACE "No‽ 3"
	else:
		log TRACE "Yes!"
state foo bar:
	saved
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 2"
	if saved state foo bar:
		log TRACE "No‽ 4"
	else:
		log TRACE "Yes!"

log TRACE Set to ONE
set state one foo bar
block:
	if saved state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 5"
log TRACE Set to TWO
set state two foo bar
on state * three foo bar:
	log TRACE Set to FOUR
	try:
		set state four foo bar
		log DEBUG "No! (No shit happened.)"
	catch StateChangeError:
		log DEBUG "Yes! (Shit happens.)"
block:
	try:
		log TRACE Set to THREE
		set state three foo bar
	catch:
		log DEBUG "No! Error! Woe!"
list state
list state foo bar
block:
	if state three foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 8"
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 7"
block:
	if last state two foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 6"
on whatever:
	var state x foo bar
	log TRACE We got $x
trigger whatever :sync
list state
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
load_module("errors")

run("persist1",input)

