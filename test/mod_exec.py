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
from moat.statement import DoNothingHandler, main_words

from test import run

input = u"""\
on test me:
	log DEBUG "Parallel MoaT handler"
on run test:
	exec test.exec.called one $also
list on
trigger run test:
	param also two
	sync
wait :for 0.1
list on
trigger test me
wait :for 0.1
shutdown
"""

main_words.register_statement(DoNothingHandler)
main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("trigger")
load_module("on_event")
load_module("exec")
load_module("ifelse")
load_module("bool")
load_module("data")
load_module("logging")
load_module("state")
load_module("wait")

run("exec",input)

