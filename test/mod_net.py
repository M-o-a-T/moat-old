#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module,Load
from moat.statement import main_words
from moat.check import register_condition
from test import run

input = """\
async:
	connect net foop localhost 50334
wait BAD:
	for 0.2
	debug force
block:
	if exists net connection foop:
		log ERROR No1
		del net foop
	else:
		log TRACE Yes

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
on net disconnect baz zaz *who:
	log TRACE dis baz zaz $who
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
		log ERROR No2
	else:
		log TRACE Yes
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
