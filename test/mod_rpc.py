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
from homevent.module import load_module,Load
from homevent.statement import main_words
from homevent.check import register_condition
from homevent.logging import log,DEBUG
from test import run
from gevent import spawn,sleep,event

import rpyc
import sys
from traceback import print_exc

got_something = event.AsyncResult()

def tester():
	sleep(0.2)
	c = rpyc.connect("localhost",56478)

	def called(**k):
		for a,b in k.iteritems():
			log("TEST",DEBUG, "CB %s: %s" % (a,b))
	cb = c.root.monitor(called,*("wait start * some time".split()))

	def logged(level,*a):
		log("TEST", DEBUG, "The logger says: <%d> %s" % (level,"¦".join((str(x) for x in a))))
		got_something.set(a)
	cm = c.root.logger(logged,"hello",DEBUG)

	for x in c.root.list():
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.list("rpc","server"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.list("rpc","server","foo"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.list("rpc","connection","foo","n1"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")

	try:
		c.root.command("fuubar","This is not found.")
	except Exception as e:
		log("TEST",DEBUG,"YES Got an error")
	else:
		log("TEST",DEBUG,"NO Got no error")
	c.root.command("log","DEBUG","This is logged.")
	c.root.command("var","state","get_me","the","tester")
	log("TEST",DEBUG,"The value is: "+c.root.var("get_me"))
	c.root.command("trigger","send","logger")
	got_something.get()
	c.root.command("del","wait","shutdown")
	cb.cancel()
	cm.cancel()
	c.close()
def gtester():
	try:
		tester()
	except Exception:
		print_exc()
j = spawn(gtester)

input = """\
listen rpc foo 56478
state the tester :value Test123
on send logger:
	log DEBUG hello This is a test
try:
	wait shutdown:
		for 5
		debug force
wait foo b:
	for 1
	debug force
shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("wait")
load_module("logging")
load_module("on_event")
load_module("net")
load_module("data")
load_module("block")
load_module("rpc")
load_module("state")
load_module("errors")
load_module("trigger")

run("rpc",input)


import sys
sys.exit(0)
