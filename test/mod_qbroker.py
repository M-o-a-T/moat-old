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
import qbroker; qbroker.setup(gevent=True)
from qbroker.unit import CC_DICT
import asyncio
import aiogevent

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

seen=False

@asyncio.coroutine
def event_cb(*a,**k):
	global seen
	if k['event'] == ['wait', 'state', 'shutdown'] and k['state'] == 'cancel':
		seen = 1

def tester():
	sleep(0.3)
	qb = qbroker.make_unit_gevent(app="test.qbroker", amqp=dict(server=dict(virtualhost="/test",login="test",password="test")))
	qb.register_alert_gevent("moat.event.#", event_cb, call_conv=CC_DICT)
	r1 = qb.rpc_gevent("moat.list", _timeout=1)
	r2 = qb.rpc_gevent("moat.list", args=("qbroker","connection"), _timeout=1)
	r3 = qb.rpc_gevent("moat.cmd", args=("list","qbroker","connection"), _timeout=1)
	r4 = qb.rpc_gevent("moat.cmd", args=("list","qbroker","connection","foo"), _timeout=1)
	r5 = qb.rpc_gevent("moat.cmd", args=("del","wait","shutdown"), _timeout=1)
	sleep(0.3)
	qb.stop_gevent()
def gtester():
	try:
		tester()
	except Exception:
		print_exc()

input = """\
log ERROR Start
connect qbroker foo localhost:
	user test test
	vhost "/test"
log ERROR connected
try:
	wait shutdown:
		for 100
		debug force
wait foo b:
	for 1000
	debug force
shutdown
"""

main_words.register_statement(ShutdownHandler)
main_words.register_statement(Load)

load_module("wait")
load_module("logging")
#load_module("on_event")
load_module("net")
load_module("data")
load_module("block")
load_module("qbroker")
load_module("state")
load_module("errors")
#load_module("trigger")
load_module("help")

k = spawn(run,"qbroker",input)
j = spawn(gtester)
f = aiogevent.wrap_greenlet(j, loop=qbroker.loop)
#qbroker.loop.run_until_complete(f)
aiogevent.yield_future(f)
assert seen

try: k.kill()
finally: k.join()
try: j.kill()
finally: j.join()

import sys
sys.exit(0)
