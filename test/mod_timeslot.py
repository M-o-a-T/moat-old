#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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
from moat.module import load_module
from moat.statement import main_words
from test import run

input = """\
#log TRACE
on timeslot begin foo bar:
	var timeslot X foo bar
	if equal $X "during":
		log TRACE Yes
	else:
		log ERROR No2 $X
	if in timeslot foo bar:
		log TRACE Yes
	else:
		log ERROR No2a

on timeslot end foo bar:
	wait GOT EVENT B:
		for 0.1
	var timeslot X foo bar
	if equal $X "next":
		log TRACE Yes
	else:
		log ERROR No9 $X
	if in timeslot foo bar:
		log ERROR No9a
	else:
		log TRACE Yes

list timeslot
timeslot foo bar:
	every 10
	for 2
	stopped
list timeslot foo bar

block:
	if running timeslot foo bar:
		var timeslot X foo bar
		log ERROR NoS $X
	else:
		log TRACE Yes

start timeslot foo bar
block:
	if running timeslot foo bar:
		log TRACE Yes
	else:
		var timeslot X foo bar
		log ERROR NoR $X

wait A before: for 9.5
list timeslot foo bar
block:
	var timeslot X foo bar
	if equal $X "next":
		log TRACE Yes
	else:
		log ERROR No4 $X
	if in timeslot foo bar:
		log ERROR No4a
	else:
		log TRACE Yes

wait B during: for 1
list timeslot foo bar
block:
	var timeslot X foo bar
	if equal $X "during":
		log TRACE Yes
	else:
		log ERROR No1 $X
	if in timeslot foo bar:
		log TRACE Yes
	else:
		var timeslot X foo bar
		log ERROR No1a

wait C after: for 2
list timeslot foo bar
block:
	var timeslot X foo bar
	if equal $X "next":
		log TRACE Yes
	else:
		log ERROR No4 $X
	if in timeslot foo bar:
		log ERROR No4a
	else:
		log TRACE Yes

wait D during again: for 8
list timeslot foo bar
block:
	var timeslot X foo bar
	if equal $X "during":
		log TRACE Yes
	else:
		log ERROR No5 $X
	if in timeslot foo bar:
		log TRACE Yes
	else:
		log ERROR No5a

stop timeslot foo bar
block:
	var timeslot X foo bar
	if equal $X "off":
		log TRACE Yes
	else:
		log ERROR No6 $X
	if in timeslot foo bar:
		log ERROR No6a
	else:
		log TRACE Yes

list timeslot foo bar
del timeslot foo bar
block:
	if exists timeslot foo bar:
		log ERROR No7
	else:
		log TRACE Yes

shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("timeslot")
load_module("block")
load_module("data")
load_module("logging")
load_module("wait")
load_module("tests")
load_module("ifelse")
load_module("bool")
load_module("on_event")

run("timeslot",input)

