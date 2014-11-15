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

from homevent import patch;patch()
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
state foo bar
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 2"

log TRACE Set to ONE
set state one foo bar
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
on state * twohalf foo bar:
	log TRACE Set to FOUR
	set state fourtoo foo bar
block:
	try:
		log TRACE Set to TWOHALF
		set state twohalf foo bar
	catch:
		log DEBUG "No! Error Propagation!"
block:
	try:
		log TRACE Set to THREE
		set state three foo bar
	catch:
		log DEBUG "No! Error! Woe!"
wait: for 0.1
list state
list state foo bar
block:
	if state three foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 3"
block:
	if exists state foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 4"
block:
	if last state twohalf foo bar:
		log TRACE "Yes!"
	else:
		log TRACE "No‽ 5"
on whatever:
	var state x foo bar
	log TRACE We got $x
trigger whatever :sync
del state foo bar
list state
shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("state")
load_module("block")
load_module("wait")
load_module("data")
load_module("on_event")
load_module("logging")
load_module("ifelse")
load_module("trigger")
load_module("errors")

run("state",input)

