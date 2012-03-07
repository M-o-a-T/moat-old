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

from homevent.times import slot_update,unixtime,now
from homevent.geventreactor import DelayedCall,deferToGreenlet,GeventReactor,Reschedule

import gevent
from gevent.event import AsyncResult

from bisect import insort


slot = None
GRAN = 20
def current_slot():
	if slot is None: return slot
	return slot/GRAN
	
class FakeDelayedCall(DelayedCall):
	"""a delayedcall which won't actually obey time"""
	"""The interesting stuff happens inside the reactor"""
	pass

class TestReactor(GeventReactor):
	"""A subclass of geventreactor which supports fake timeouts"""
	# now = 1049519228 # 2003-04-05 06:07:08 UTC
	def seconds(self):
		return unixtime(now())
	def realSeconds(self):
		return unixtime(now(True))
		
	def callLater(self,*args,**kw):
		if isinstance(args[0],DelayedCall):
			c = args[0]
			try:
				self._callqueue.remove(c)
			except ValueError:
				pass
		else:
			c = DelayedCall(self,self.seconds()+args[0],args[1],args[2:],kw,seconds=self.seconds)
		insort(self._callqueue,c)
		self.reschedule()
		return c
	def mainLoop(self):
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
						delay = now+0.01
						slot_update(c.time)
					else:
						delay = c.getTime()
						now = self.realSeconds()
					self._wake = delay
					delay -= now
				else:
					self._wake = now+10
					delay = 10
				if delay > 10:
					raise RuntimeError("Real Delay too large: %s"%(delay,))
				try:
					self._wait = 1
					gevent.sleep(max(0,delay))
				except Reschedule:
					continue
				finally:
					self._wait = 0

				now = seconds()
				while callqueue:
					c = callqueue[0]
					if c.getTime() > now and not isinstance(c,FakeDelayedCall):
						break
					del callqueue[0]
					try:
						c()
					except gevent.GreenletExit:
						raise
					except:
						log.msg('Unexpected error in main loop.')
						log.err()
		except (gevent.GreenletExit,KeyboardInterrupt):
			pass

		from twisted.python import log
		log.msg('Main loop terminated.')
		self.fireSystemEvent('shutdown')

def install():
	"""Configure the twisted mainloop to be run using geventreactor."""
	reactor = TestReactor()
	from twisted.internet.main import installReactor
	installReactor(reactor)

