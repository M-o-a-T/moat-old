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

import six
if six.PY2:
	import sys; sys.exit(121)

from moat import patch;patch()
from moat.reactor import ShutdownHandler
from moat.module import load_module,Load
from moat.statement import main_words
from moat.check import register_condition
from moat.logging import log,DEBUG
from test import run
from gevent import spawn,sleep,event

import rpyc
import sys
from traceback import print_exc

got_something = event.AsyncResult()

class LogStream(object):
	buf = ""
	def exposed_write(self,s):
		i = s.find("\n")
		while i >= 0:
			log("TEST",DEBUG,">>>",self.buf+s[:i])
			self.buf = ""
			s = s[i+1:]
			i = s.find("\n")
		self.buf += s

def tester():
	sleep(0.2)
	c = rpyc.connect("localhost",56478)

	def called(**k):
		for a,b in k.items():
			log("TEST",DEBUG, "CB %s: %s" % (a,b))
	cb = c.root.monitor(called,*("wait start * some time".split()))

	def logged(level,*a):
		log("TEST", DEBUG, "The logger says: <%d> %s" % (level,"¦".join((str(x) for x in a))))
		got_something.set(a)
	cm = c.root.logger(logged,"hello",DEBUG)

	for x in c.root.cmd_list():
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.cmd_list("rpc","server"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.cmd_list("rpc","server","foo"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")
	for x in c.root.cmd_list("rpc","connection","foo","n1"):
		log("TEST",DEBUG, repr(x))
	log("TEST",DEBUG,".")

	c.root.stdout(LogStream())
	c.root.command("help")

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
		for 1
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
load_module("help")

run("rpc",input)

import sys
sys.exit(0)
