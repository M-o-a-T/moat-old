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

"""\
This code implements access to collections.

"""

from __future__ import division,absolute_import

import rpyc
import sys
from types import GeneratorType

from datetime import datetime
import os

from homevent.base import Name,flatten

from gevent import spawn
from gevent.queue import Queue
from optparse import OptionParser
parser = OptionParser(conflict_handler="resolve")
parser.add_option("-h","--help","-?", action="help",
	help="print this help text")
parser.add_option("-s", "--server", dest="host", action="store",
	default="::1", help="Server to connect to")
parser.add_option("-p", "--port", dest="port", action="store",
	type="int",default="50005", help="port to connect to")
parser.add_option("-6", "--ipv6", dest="ipv6", action="store_true",
	default=False, help="Use IPv6")

(opts, args) = parser.parse_args()

def getter(q):
	while True:
		res = q.get()
		if res is None:
			return
		p,t = res
		if isinstance(t,datetime):
			if TESTING and t.year != 2003:
				t = "%s" % (humandelta(t-now(t.year != 2003)),)
			else:
				t = "%s (%s)" % (humandelta(t-now(t.year != 2003)),t)
			if TESTING:
				lim = 3
			else:
				lim = 4
			ti = t.rfind('.')
			if ti>0 and len(t)-ti>lim and len(t)-ti<lim+6: # limit to msec
				t = t[:ti+lim]+")"

		print p+u": "+unicode(t)

def out_one(p,c):
	q = Queue(3)
	try:
		job = spawn(getter,q)
		flatten(q,(c,),p)
	finally:
#					with log_wait("list "+str(event)):
		q.put(None)
		job.join()

	
c = rpyc.connect(opts.host, opts.port, ipv6=opts.ipv6)
for x in c.root.cmd_list(*args):
	if x is None:
		print "(None?)"
		continue
		
	if len(x) == 2:
		a,b = x
		a = str(a)
		out_one(a,b)
#		if hasattr(b,"list"):
#			for bb in b.list():
#				print a,bb
#			continue
#		else:
#			print a,b
	else:
		if len(x) == 1 and isinstance(x[0],Name):
			x=str(x[0])
		print x

