# -*- coding: utf-8 -*-
from __future__ import division

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
	This module holds Twisted support stuff.
	"""

from homevent.geventreactor import DelayedCall,deferToGreenlet,GeventReactor,Reschedule

import gevent
import sys
from gevent.event import AsyncResult

from bisect import insort

class FakeDelayedCall(DelayedCall):
	"""a DelayedCall which won't actually obey time"""
	"""The interesting stuff happens inside the reactor"""
	pass
def realGetSeconds(self):
	from homevent.times import unixtime,now
	return self.getTime() - unixtime(now(True))
FakeDelayedCall.getSeconds = DelayedCall.getSeconds
DelayedCall.getSeconds = realGetSeconds

class TestReactor(GeventReactor):
	"""A subclass of geventreactor which supports fake timeouts"""
	# now = 1049519228 # 2003-04-05 06:07:08 UTC
	def seconds(self):
		from homevent.times import unixtime,now
		return unixtime(now())
	def realSeconds(self):
		from homevent.times import unixtime,now
		return unixtime(now(True))
		
	def callLater(self,*args,**kw):
		if isinstance(args[0],DelayedCall):
			c = args[0]
			try:
				self._callqueue.remove(c)
			except ValueError:
				pass
		else:
			c = DelayedCall(self,self.realSeconds()+args[0],args[1],args[2:],kw,seconds=self.realSeconds)
		insort(self._callqueue,c)
		self.reschedule()
		return c

	# Copy from geventreactor, but using "real" time
	def callFromGreenlet(self,func,*args,**kw):
		c = DelayedCall(self,self.realSeconds(),func,args,kw,seconds=self.realSeconds)
		insort(self._callqueue,c)
		self.reschedule()
		return c

	def mainLoop(self):
		from homevent.times import slot_update
		"""This main loop yields to gevent until the end, handling function calls along the way."""
		self.greenlet = gevent.getcurrent()
		callqueue = self._callqueue
		seconds = self.seconds
		try:
			while 1:
				self._wait = 0
				now = seconds()
				if len(callqueue) > 0:
					c = callqueue[0]
					if isinstance(c,FakeDelayedCall):
						self._wake = seconds()
						delay = 0.01
					else:
						delay = c.getTime()
						now = self.realSeconds()
						self._wake = delay
						delay -= now
				else:
					c = None
					self._wake = now+10
					delay = 10
				try:
					self._wait = 1
					gevent.sleep(max(0,delay))
				except Reschedule:
					continue
				else:
					if isinstance(c,FakeDelayedCall):
						slot_update(c.time)
				finally:
					self._wait = 0

				while callqueue:
					c = callqueue[0]
					if isinstance(c,FakeDelayedCall):
						now = seconds()
					else:
						now = self.realSeconds()
					if c.getTime() > now:
						break
					del callqueue[0]
					try:
						c()
					except gevent.GreenletExit:
						raise
					except:
						from twisted.python import log
						log.msg('Unexpected error in main loop.')
						log.err()
		except (gevent.GreenletExit,KeyboardInterrupt):
			pass

		from twisted.python import log
		log.msg('Main loop terminated.')
		self.fireSystemEvent('shutdown')

	def reschedule(self):
		if self._wait and len(self._callqueue) > 0: # don't look at the time
			gevent.kill(self.greenlet,Reschedule)

def install():
	"""Configure the twisted mainloop to be run using geventreactor."""
	reactor = TestReactor()
	from twisted.internet.main import installReactor
	installReactor(reactor)

