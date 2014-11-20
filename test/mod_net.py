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
from homevent.module import load_module,Load
from homevent.statement import main_words
from homevent.check import register_condition
from test import run

input = """\
async:
	connect net foop localhost 50334
wait BAD:
	for 0.2
	debug force
block:
	if exists net connection foop:
		log DEBUG No1
		del net foop
	else:
		log DEBUG Yes

on net connect foo:
	send net foo "bar"
	wait OUT:
		for 0.1
		debug force
	list net connection
	list net connection foo
	del net connection foo
on net connect baz zaz *who:
	send net "quux":
		to baz zaz $who
	wait IN:
		for 0.1
		debug force
	list net connection baz zaz $who
	del net connection baz zaz $who
on net disconnect foo:
	log TRACE dis foo
on net disconnect baz zaz:
	log TRACE dis baz zaz
wait BEFORE:
	for 0.2
	debug force
listen net localhost 50345 :name baz zaz
async:
	connect net foo localhost 50333
wait AFTER:
	for 0.8
	debug force
log TRACE ending
list net connection
block:
	if exists net connection foo:
		list net connection foo
		del net connection foo
		log DEBUG No2
	else:
		log DEBUG Yes
wait END:
	for 0.2
shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("wait")
load_module("logging")
load_module("on_event")
load_module("net")
load_module("data")
load_module("block")
load_module("ifelse")

run("net",input)


import sys
sys.exit(0)
