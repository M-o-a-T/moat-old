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

class Timeslotted(object):
	pass
#	def slot_up(self):
#		pass
#	def slot_down(self):
#		pass

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
	interval = None # time between slots; set externally

	def __init__(self,parent,name):
		self.ctx = parent.ctx
		self.parent = parent
		super(Timeslot,self).__init__(*name)

	def __repr__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.running)

	def list(self):
		yield ("name"," ".join(unicode(x) for x in self.name))
		yield ("run",self.running)
		if self.interval is not None:
			yield ("interval"," ".join(str(x) for x in self.interval))
		yield ("duration",self.duration)
		if self.last is not None:
			yield ("last",humandelta(now()-self.last))
		if self.next is not None:
			yield ("next",humandelta(self.next-now()))
		if self.slotter is not None:
			yield ("slot",(unixdelta(self.next-now()))/self.duration)

	def info(self):
		if self.running not in ("off","error"):
			tm = unixdelta(self.next-now())
		elif self.last is not None:
			tm = unixdelta(now()-self.last)
		else:
			tm = "never"
		return "%s %s" % (self.running,tm)

	def do_pre(self):
		self.waiter = None
		if self.running != "next" or self.slotter is not None:
			log(ERROR,"timeslot error pre",self.running)
			return

		self.running = "pre"
		if self.next is None:
			self.next = now()
		self.last = self.next
		d = process_event(Event(self.ctx,"timeslot","begin",*self.name))
		def post(_):
			if self.running == "pre":
				self.running = "during"
				self.next += dt.timedelta(0,self.duration)
				self.slotter = callLater(False,self.next, self.do_post)
			elif self.running not in ("off","error"):
				log(ERROR,"timeslot error pre2",self.running)
			else:
				self.next = None
			return _
		d.addCallback(post)
		d.addErrback(self.dead)
	
	def do_sync(self):
		self.down()
		self.running = "during"
		self.next = now()+dt.timedelta(0,self.duration/2)
		self.slotter = callLater(False,self.next, self.do_post)
	
	def do_post(self):
		self.slotter = None
		if self.running != "during" or self.waiter is not None:
			log(ERROR,"timeslot error post",self.running)
			return

		self.running = "post"
		d = process_event(Event(self.ctx,"timeslot","end",*self.name))
		def post(_):
			if self.running == "post":
				self.running = "next"
				self.next = time_delta(self.interval, now=self.next)-dt.timedelta(0,self.duration)
				self.waiter = callLater(False, self.next, self.do_pre)
			elif self.running not in("off","error"):
				log(ERROR,"timeslot error post2",self.running)
			return _
		d.addCallback(post)
		d.addErrback(self.dead)


	def dead(self,_):
		self.running = "error"
		process_failure(_)
		self.down()
		simple_event(self.ctx,"timeslot","error",*self.name)


	def delete(self,ctx):
		self.down()
		self.delete_done()
		return


	def is_up(self):
		return self.running not in ("off","error")
	def is_in(self):
		return self.running in ("pre","during","post")
	def is_out(self):
		return self.running == "next"
		
	def up(self, resync=False):
		if self.running not in ("off","error"):
			if not resync:
				raise AlreadyRunningError(self)
		if resync:
			self.do_sync()
		else:
			self.running = "next"
			self.next = time_delta(self.interval, now=self.last)
			self.waiter = callLater(False, self.next, self.do_pre)
#			self.parent.slot_up()
		
	def maybe_up(self, resync = False):
		if self.running not in ("off","error"):
			return
		if self.last is not None:
			self.running = "next"
			self.next = time_delta(self.interval, now=self.last)
			self.waiter = callLater(False, self.next, self.do_pre)

	def down(self):
		if self.waiter:
			self.waiter.cancel()
			self.waiter = None
		if self.slotter:
			self.slotter.cancel()
			self.slotter = None
#		self.parent.slot_down()
		self.running = "off"
		self.next = None


