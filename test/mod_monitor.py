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
on monitor update foo bar:
	if null $last_value:
		log TRACE First value is $value
	else:
		log TRACE Go from $last_value to $value
monitor test 0 100 2:
	name foo bar
	delay for 0.4
wait: for 1
block:
	if waiting monitor foo bar:
		log ERROR No0
	else:
		log TRACE Yes
list monitor
list monitor foo bar
wait: for 0.8
del monitor foo bar
list monitor

on monitor checking baz zaz:
	set monitor 10 baz zaz
	wait bazzaz A: for 0.2
	set monitor 13 baz zaz
	wait bazzaz B: for 0.2
	set monitor 14 baz zaz
	
monitor passive:
	name baz zaz
	delay for 0.9
	require 2 2
list monitor baz zaz

wait: for 0.1
block:
	if waiting monitor baz zaz:
		log TRACE Yes
	else:
		log ERROR No1
wait: for 0.5
block:
	if waiting monitor baz zaz:
		log ERROR No2
	else:
		log TRACE Yes
list monitor baz zaz
log DEBUG XXX delete baz zaz
del monitor baz zaz

input monitest fake
input monitest2 fake
output monitest fake
output monitest2 fake
set output 1 monitest
set output 2 monitest2

# The alternate solution would be a passive monitor
# which gets triggered by the event that's emitted
# when setting the variable, but we already test all
# components of that solution elsewhere.
monitor input monitest:
	delay for 0.2
	name moni test
monitor input monitest2:
	delay for 0.2
	name moni test2
	delta
wait :for 0.1
set output 2 monitest
set output 1 monitest2
wait :for 0.2
set output 3 monitest
set output 2 monitest2
wait :for 0.2
set output 4 monitest
set output 5 monitest2
wait :for 0.2
set output 5 monitest
set output 12 monitest2
list monitor
list monitor moni test
list monitor moni test2
wait :for 0.2
del monitor moni test
del monitor moni test2

shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("monitor")
load_module("block")
load_module("data")
load_module("logging")
load_module("wait")
load_module("tests")
load_module("ifelse")
load_module("bool")
load_module("on_event")

run("monitor",input)

