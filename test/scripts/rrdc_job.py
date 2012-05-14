#!/usr/bin/python

"""Simple server that listens on port 6000 and echos back every input to the client.

Connect to it with:
telnet localhost 6000

Terminate the connection by terminating telnet (typically Ctrl-] and then 'quit').
"""
import gevent
from gevent.server import StreamServer

def rrdc_me(socket, address):
	print ('New connection from %s:%s' % address)
	fileobj = socket.makefile()

	line = fileobj.readline()
	fileobj.write("0 Yes\n")
	fileobj.flush()

	line = fileobj.readline()
	fileobj.write("2 Nonsense follows\n")
	fileobj.write("Nonsense\n")
	fileobj.write("More Nonsense\n")
	fileobj.flush()

	while True:
		line = fileobj.readline()
		if line is None or line == "":
			break
		fileobj.write("-123 No\n")
		fileobj.flush()


if __name__ == '__main__':
	# to make the server use SSL, pass certfile and keyfile arguments to the constructor
	s1 = StreamServer(('localhost', 52442), rrdc_me)
	s1.start()

	gevent.sleep(30)
	s1.stop()
