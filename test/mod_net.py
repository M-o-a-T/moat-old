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
from test import run

input = """\
async:
	connect net foop localhost 50334
wait BAD:
	for 0.2
	debug force
block:
	if exists net foop:
		log DEBUG No1
		del net foop
	else:
		log DEBUG Yes

on net connect foo:
	send net foo "bar"
	list net
	list net foo
	del net foo
on net connect baz zaz *who:
	send net "quux":
		to baz zaz $who
	list net baz zaz $who
	del net baz zaz $who
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
list net
block:
	if exists net foo:
		list net foo
		del net foo
		log DEBUG No2
	else:
		log DEBUG Yes
wait END:
	for 0.2
shutdown
"""

h.main_words.register_statement(ShutdownHandler)
h.main_words.register_statement(Load)
h.register_condition(ModuleExists)

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
