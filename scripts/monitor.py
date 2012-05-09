# -*- coding: utf-8 -*-
import rpyc
import sys
import gevent
from gevent.queue import Queue
from rpyc.core.service import VoidService
from homevent import gevent_rpyc
gevent_rpyc.patch_all()

host="::1"
port=50005
if len(sys.argv) > 1:
	port = int(sys.argv[-1])
if len(sys.argv) > 2:
	host = sys.argv[-2]

class ExitService(VoidService):
	def on_disconnect(self,*a,**k):
		sys.exit()
	

c = rpyc.connect(host, port, ipv6=True, service=ExitService)
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
