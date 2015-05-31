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

log amqp DEBUG:
	name test foo
	exchange he_exc

# amqp => homevent
# translate amqte.x.y.z to amam.x.y.z
listen amqp test foo:
	name foo lish
	exchange he_exc
	prefix amam 
	topic "amqte.#"
	strip 1

# homevent => amqp
# translate hey.x to amqte.x
tell amqp test foo:
	filter hey *
	exchange he_exc
	prefix amqte
	strip 1

# send everything as-is
tell amqp test foo:
	exchange he_exc

start amqp test foo

on amam ho:
	del wait foo b

on wait cancel foo b:
	log TRACE Yes
on wait done foo b:
	log ERROR No b2

async:
	wait foo a:
		for 0.2
		debug force
	trigger hey ho

async:
	wait foo b:
		for 0.5
		debug force
	log ERROR No b1

list amqp listener
list amqp listener foo lish
list amqp connection
list amqp connection test foo
list worker
list worker 7
list log
list log AMQPlogger x2
wait:
	for 0.6
	debug force

stop amqp test foo
del amqp listener foo lish
# canceling the worker doesn't work yet

listen amqp test foo:
	name foo bus in
	exchange he_bus
	shunt

tell amqp test foo:
	name foo bus out
	exchange he_bus
	shunt

# check for actual messages
listen amqp test foo:
	name foo bus in monitor
	exchange he_bus
	prefix moni
	topic "some.#"
	# this will end up on the bus again
	# the topic filter is required to prevent a loop

start amqp test foo

async:
	wait foo mon:
		for 0.5
		debug force
	log ERROR no foo mon
async:
	wait foo in:
		for 0.5
		debug force
	log ERROR no foo in

on moni some thing:
	del wait foo mon
	log TRACE YES mon in
on some thing:
	del wait foo in
	log TRACE YES in
trigger some thing
wait:
	for 0.6
	debug force

# homevent => amqp
# translate hey.x to amqte.x

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
