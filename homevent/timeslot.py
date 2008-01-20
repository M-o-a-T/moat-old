# -*- coding: utf-8 -*-

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division

"""\
This code contains the framework for timing regular events.

"""

from homevent.statement import AttributedStatement, Statement
from homevent.event import Event
from homevent.run import process_event,process_failure,register_worker
from homevent.reactor import shutdown_event
from homevent.times import time_delta, time_until, unixdelta, now, \
	humandelta
from homevent.base import Name
from homevent.twist import deferToLater, callLater
from homevent.context import Context
from homevent.logging import log,TRACE,DEBUG,ERROR
from homevent.collect import Collection,Collected

from time import time
import os
from twisted.python import failure
from twisted.internet import defer
import datetime as dt

class Timeslots(Collection):
    name = "timeslot"
Timeslots = Timeslots()
Timeslots.can_do("del")

class TimeslotError(RuntimeError):
    def __init__(self,w):
        self.timeslot = w
    def __str__(self):
        return self.text % (" ".join(str(x) for x in self.timeslot.name),)
    def __unicode__(self):
        return self.text % (" ".join(unicode(x) for x in self.timeslot.name),)

class AlreadyRunningError(TimeslotError):
    text = u"A The timer ‹%s› is already active"


class Timeslot(Collected):
	"""This is the thing that watches."""
	storage = Timeslots.storage

	last = None # last time I was called / next time I will be called
	next = None # last time I was called / next time I will be called
	running = "off" # state
		# off: not running
		# next: wait for next event, not in slot
		# pre: wait for event trigger, in slot
		# during: event in progress, in slot (obviously)
		# post: after event, in slot
	waiter = None # trigger for next event
	slotter = None # trigger for time slot
	shift = 0.5 # position during the slot when the event will trigger
	duration = 1 # length of slot
	interval = None # time between slots

	def __init__(self,parent,name):
		self.ctx = parent.ctx
		super(Timeslot,self).__init__(*name)

	def __repr__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.running)

	def list(self):
		yield ("name"," ".join(unicode(x) for x in self.name))
		yield ("run",self.running)
		if self.last is not None:
			yield ("last",humandelta(unixdelta(now()-self.last)))
		if self.next is not None:
			yield ("next",humandelta(unixdelta(self.next-now())))
		if self.slotter is not None:
			yield ("slot",(unixdelta(now()-self.next))/self.duration)

	def info(self):
		if self.running != "off":
			tm = unixdelta(self.last-now())
		elif self.last is not None:
			tm = unixdelta(now()-self.last)
		else:
			rm = "never"
		return "%s %s" % (self.running,tm)

	def do_pre(self):
		self.waiter = None
		if self.running == "next" and self.slotter is None:
			self._do_pre()
		else:
			self.waiter = None
			log(ERROR,"timeslot error next",self.running)

	def _do_pre(self):
		self.waiter = None
		self.running = "pre"
		self.next = now()
		self.slotter = callLater(False,unixdelta(self.next+dt.timedelta(0,self.duration*self.shift)-now()), self.do_event)
	
	def do_event(self):
		self.slotter = None
		if self.running == "pre":
			self._do_event()
		elif self.running != "off":
			log(ERROR,"timeslot error pre",self.running)

	def _do_event(self):
		self.running = "during"
		d = process_event(Event(self.ctx,"timeslot",*self.name))
		def post(_):
			if self.running == "during":
				self.running = "post"
				self.slotter = callLater(False,unixdelta(self.next+dt.timedelta(0,self.duration)-now()), self.do_post)
			elif self.running != "off":
				log(ERROR,"timeslot error during",self.running)
			return _
		d.addBoth(post)
		d.addErrback(process_failure)
	
	def do_post(self):
		self.slotter = None
		if self.running == "post":
			self._do_post()
		elif self.running != "off":
			log(ERROR,"timeslot error post",self.running)

	def _do_post(self):
		self.running = "next"
		self.last = self.next
		self.next = time_delta(self.interval, now=self.next)
		self.waiter = callLater(False, unixdelta(self.next-now()), self._do_pre)

	def delete(self,ctx):
		self.down()
		self.delete_done()
		return


	def up(self, resync = False):
		if self.running != "off":
			if not resync:
				raise AlreadyRunningError(self)
		if resync:
			old_run = self.running
			self.down()
			self.next = now()-dt.timedelta(0,self.duration*self.shift)
			if old_run in ("during","post"):
				self._do_post()
			else:
				self._do_event()
		else:
			self.running = "next"
			self.next = time_delta(self.interval, now=self.last)
			self.waiter = callLater(False, unixdelta(self.next-now()), self._do_pre)
		

	def down(self):
		if self.waiter:
			self.waiter.cancel()
			self.waiter = None
		if self.slotter:
			self.slotter.cancel()
			self.slotter = None
		self.running = "off"


