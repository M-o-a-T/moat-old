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
from homevent.logging import log,DEBUG
from test import run
from gevent import spawn,sleep,event

import rpyc
import sys
from traceback import print_exc

input = """\
connect amqp localhost:
	name test foo
	user "/test" test test

on amqp connect test foo:
	wait for 0.2:
		debug force
	trigger hey ho

# amqp => homevent
listen amqp test foo:
	name foo lish
	exchange he_exc
	prefix amam 
	topic "amqte.#"

# homevent => amqp
tell amqp hey *:
	name test foo
	exchange he_exc
	prefix amqte

start amqp test foo

on amam amqte hey ho:
	del wait foo b

on wait cancel foo b:
	log TRACE Yes
on wait done foo b:
	log ERROR No

async:
	wait foo a:
		for 0.2
		debug force
	trigger hey ho

async:
	wait foo b:
		for 1
		debug force
	log ERROR No

list amqp listener
list amqp listener foo lish
list amqp connection
list amqp connection test foo
wait:
	for 1

shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("amqp")
load_module("wait")
load_module("logging")
load_module("on_event")
load_module("net")
load_module("data")
load_module("block")
load_module("state")
load_module("errors")
load_module("trigger")
load_module("help")

run("amqp",input)


import sys
sys.exit(0)
