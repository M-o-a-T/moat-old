#!/usr/bin/python

"""Simple server that listens on port 6000 and echos back every input to the client.

Connect to it with:
telnet localhost 6000

Terminate the connection by terminating telnet (typically Ctrl-] and then 'quit').
"""
import gevent
from gevent.server import StreamServer

def discard(socket, address):
	print(('New connection from %s:%s' % address))
	fileobj = socket.makefile()
	while True:
		line = fileobj.readline()
		if not line: return
		print(("got %r" % line))


if __name__ == '__main__':
	# to make the server use SSL, pass certfile and keyfile arguments to the constructor
	s1 = StreamServer(('localhost', 59068), discard)
	s1.start()
	s2 = StreamServer(('localhost', 59067), lambda a,b:None)
	s2.start()

	gevent.sleep(30)
	s1.stop()
	s2.stop()
