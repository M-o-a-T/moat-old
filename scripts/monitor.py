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

from __future__ import division,absolute_import

import rpyc
import sys
import gevent
from gevent.queue import Queue
from rpyc.core.service import VoidService
from homevent import gevent_rpyc
import sys,signal

gevent_rpyc.patch_all()

from optparse import OptionParser
parser = OptionParser(conflict_handler="resolve")
parser.add_option("-h","--help","-?", action="help",
	help="print this help text")
parser.add_option("-s", "--server", dest="host", action="store",
	default="::1", help="Server to connect to")
parser.add_option("-p", "--port", dest="port", action="store",
	type="int",default="50005", help="port to connect to")

class ExitService(VoidService):
	def on_disconnect(self,*a,**k):
		sys.exit()
	
(opts, args) = parser.parse_args()
if args:
	raise RuntimeError("don't pass arguments")

c = rpyc.connect(opts.host, opts.port, ipv6=True, service=ExitService)
c._channel.stream.sock.settimeout(None)
d = []
maxl = 0
q = Queue()

def called(**k):
	try:
		if k["event"][-1] == "test" and k["event"][-2] == "motion":
			return
	except:
		pass
	for a,b in k.iteritems():
		print a,b
	print ""
	sys.stdout.flush()

def q_called(**k):
	q.put((called,[],k))
cb = c.root.monitor(q_called)

def logged(level,*a):
	print u"<%d> %s" % (level,u"¦".join((str(x) for x in a)))
	sys.stdout.flush()
def q_logged(*a):
	q.put((logged,a,{}))
cm = c.root.logger(q_logged,None,0)

sigged = False
def do_shutdown(a,b):
	global sigged
	sigged = True
signal.signal(signal.SIGINT,do_shutdown)
signal.signal(signal.SIGTERM,do_shutdown)
while not sigged:
	p,a,k = q.get()
	p(*a,**k)

