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
from moat.logging import log,DEBUG
from test import run
from gevent import spawn,sleep,event

import os

host=os.environ.get('AMQP_HOST',"localhost")
input = """\
connect amqp "{}":
	name test foo
	user "test" test test

on amqp connect test foo:
	if exists wait delay amqp:
		del wait delay amqp

if not exists amqp connection test foo:
	log DEBUG waiting for connect
	wait delay amqp:
		for 100
		debug force

log amqp DEBUG:
	name test foo
	exchange he_exc

# amqp => moat
# translate amqte.x.y.z to amam.x.y.z
listen amqp test foo:
	name foo lish
	exchange he_exc
	prefix amam 
	topic "amqte.#"
	strip 1

# moat => amqp
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

on wait state foo b:
	if equal $state cancel:
		log TRACE Yes
	else if not equal $state start:
		log ERROR No b2 $state

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
list worker 8
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

# moat => amqp
# translate hey.x to amqte.x

shutdown
""".format(host)

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
load_module("ifelse")
load_module("bool")
load_module("help")

run("amqp",input)

import sys
sys.exit(0)
