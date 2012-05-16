#!/usr/bin/python
# -*- coding: utf-8 -*-
import rpyc
import sys
import gevent
from gevent.queue import Queue
from rpyc.core.service import VoidService
from homevent import gevent_rpyc
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
	for a,b in k.iteritems():
		print a,b
	print ""
def q_called(**k):
	q.put((called,[],k))
cb = c.root.monitor(q_called)

def logged(level,*a):
	print u"<%d> %s" % (level,u"¦".join((str(x) for x in a)))
def q_logged(*a):
	q.put((logged,a,{}))
cm = c.root.logger(q_logged,None,0)

while True:
	p,a,k = q.get()
	p(*a,**k)
