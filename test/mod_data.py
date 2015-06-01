#!/usr/bin/python
# -*- coding: utf-8 -*-
##BP
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

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module
from moat.statement import main_words
from test import run

input = """\
list module
list module on_event
list worker
list event
list

on foo:
	if equal $one two:
		log TRACE Yes
	else:
		log ERROR No $one
	block:
		wait foo waiter:
			for 0.3
wait vorher: for 0.1
trigger foo:
	param one two
	param three 4
wait nachher: for 0.1
list wait
list wait foo waiter
wait ende: for 0.3

shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("trigger")
load_module("wait")
load_module("logging")
load_module("ifelse")
load_module("bool")
load_module("block")
load_module("data")
load_module("on_event")

run("data",input)

