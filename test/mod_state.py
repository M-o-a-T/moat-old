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
from moat.module import load_module
from moat.statement import main_words
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
on state change foo bar:
	if equal $value three:
		log TRACE Yes Set to three
block:
	try:
		log TRACE Set to THREE
		set state three foo bar
	catch:
		log DEBUG "No! Error! Woe!"
on state change foo bar:
	if equal $value twohalf:
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
load_module("bool")
load_module("trigger")
load_module("errors")

run("state",input)

