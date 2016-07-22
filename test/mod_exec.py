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
from moat.statement import DoNothingHandler, main_words

from test import run

input = u"""\
on test me:
	log DEBUG "Parallel MoaT handler"
on run test:
	exec test.exec.called one $also
on test it:
	if equal $what ever:
		log DEBUG Y what $what
	else:
		log ERROR N what $what
list on
trigger run test:
	param also two
	sync
wait :for 0.1
list on
trigger test me
wait :for 60
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
load_module("amqp")

run("exec",input)

