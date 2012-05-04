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

from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load,ModuleExists
from homevent.statement import main_words
from homevent.check import register_condition
from homevent.logging import log,DEBUG
from test import run
from gevent import spawn,sleep

import rpyc
import sys

def tester():
	sleep(0.2)
	log(DEBUG, "CONNECTING")
	c = rpyc.connect("localhost",56478)
	for x in c.root.list():
		log(DEBUG, repr(x))
	log(DEBUG,".")
	for x in c.root.list("rpc","server"):
		log(DEBUG, repr(x))
	log(DEBUG,".")
	for x in c.root.list("rpc","server","foo"):
		log(DEBUG, repr(x))
	log(DEBUG,".")
	for x in c.root.list("rpc","connection","foo","n1"):
		log(DEBUG, repr(x))
	log(DEBUG,".")

spawn(tester)

input = """\
listen rpc foo 56478
wait server:
	for 1
	debug force
wait foo:
	for 1
	debug force
shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)
register_condition(ModuleExists)

load_module("wait")
load_module("logging")
load_module("on_event")
load_module("net")
load_module("data")
load_module("block")
load_module("ifelse")
load_module("rpc")

run("rpc",input)


import sys
sys.exit(0)
