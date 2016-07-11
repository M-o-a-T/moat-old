# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This code does basic timeout handling.

timeslot FOO...
	- timeslots for FOO seconds

"""

from moat.timeslot import Timeslots, Timeslot, Timeslotted
from moat.statement import AttributedStatement, Statement, main_words,\
	global_words
from moat.module import Module
from moat.check import Check,register_condition,unregister_condition
from moat.base import Name,SName

import os

class TimeslotHandler(AttributedStatement, Timeslotted):
	name="timeslot"
	doc="A timeslot which waits for values"
	long_doc="""\
timeslot ‹name…›
	- Handle events which happen at predetermined times.
	"""

	stopped = False
	def __init__(self,*a,**k):
		super(TimeslotHandler,self).__init__(*a,**k)
		self.values = {}

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: timeslot ‹name…›')

		m = Timeslot(self, SName(event))
		if "interval" not in self.values:
			raise SyntaxError(u'Usage: timeslot ‹name…›: need to specify an interval')

		for p,v in self.values.items():
			setattr(m,p,v)
		if not self.stopped:
			return m.up()
	
class TimeslotInterval(Statement):
	name = "every"
	doc = "Interval between events"
	long_doc=u"""\
every ‹time interval›
	Set the time between two slots.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: interval ‹timespec›')
		else:
			self.parent.values['interval'] = tuple(event)
TimeslotHandler.register_statement(TimeslotInterval)

class TimeslotStopped(Statement):
	name = "stopped"
	doc = "start disabled"
	long_doc=u"""\
stopped
	Do not start the timeslot immediately;
	instead, wait for a ‹start timeslot› command.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u'Usage: stopped')
		self.parent.stopped = True
TimeslotHandler.register_statement(TimeslotStopped)

	
class TimeslotDuration(Statement):
	name = "for"
	doc = "slot length"
	long_doc=u"""\
for ‹time interval›
	The time between start and stop of this time slot.
	The default is one second.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: duration ‹time interval›')
		elif len(event) == 1:
			self.parent.values['duration'] = float(event[0])
		else:
			self.parent.values['duration'] = tuple(event)
TimeslotHandler.register_statement(TimeslotDuration)

	
class TimeslotOffset(Statement):
	name = "offset"
	doc = "Event trigger delay"
	long_doc=u"""\
offset ‹0…1›
	The moment during the time slot when the event will be triggered.
	0: at the beginning, 1: at the end. The default is 0.5.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: offset ‹0…1›')
		else:
			f = float(event[0])
			if f<0 or f>1:
				raise SyntaxError(u'Usage: offset ‹0…1›')
			self.parent.values['shift'] = f
TimeslotHandler.register_statement(TimeslotOffset)

	
class TimeslotUpdate(AttributedStatement):
	name = "update timeslot"
	doc = "change the parameters of an existing timeslot"
	long_doc="""\
This statement updates the parameters of an existing timeslot.
"""
	def __init__(self,*a,**k):
		super(TimeslotUpdate,self).__init__(*a,**k)
		self.values = {}

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) == 0:
			raise SyntaxError(u'Usage: update timeslot ‹name…›')
		if not self.params:
			raise SyntaxError(u'update timeslot: You did not specify any changes?')
		timeslot = Timeslots[SName(event)]

		for p,v in self.params.items():
			setattr(timeslot,p,v)

for cmd in (TimeslotInterval, TimeslotDuration, TimeslotOffset):
	TimeslotUpdate.register_statement(cmd)

class TimeslotStart(AttributedStatement):
	name = "start timeslot"
	doc = "Start a timeslot"
	long_doc=u"""\
start timeslot ‹name›
	This statement starts running a timeslot.
	The timeslot may not be active unless the "now" subcommand is used.
"""
	now=False

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: start timeslot ‹name…›')
		m = Timeslots[SName(event)]
		return m.up(resync=self.now)

class TimeslotNow(Statement):
	name = "now"
	doc = "immediately start or resync the slot"
	long_doc=u"""\
now
	Start running the slot immediately. (The event is triggered
	unless that has already happened during the current slot.)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u'Usage: now')
		self.parent.stopped = True
TimeslotStart.register_statement(TimeslotNow)

	
class TimeslotStop(Statement):
	name = "stop timeslot"
	doc = "Stop a timeslot"
	long_doc=u"""\
stop timeslot ‹name›
	This statement stops a timeslot handler.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: stop timeslot ‹name…›')
		m = Timeslots[SName(event)]
		return m.down()

class RunningTimeslotCheck(Check):
	name="running timeslot"
	doc="check if a timeslot is active"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if running timeslot ‹name…›")
		name = Name(*args)
		return Timeslots[name].running != "off"

class DuringTimeslotCheck(Check):
	name="in timeslot"
	doc="check if we're within a timeslot"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if in timeslot ‹name…›")
		name = Name(*args)
		return Timeslots[name].running not in ("off","next")

class VarTimeslotHandler(Statement):
	name="var timeslot"
	doc="assign a variable to the current state of a timeslot"
	long_doc=u"""\
var timeslot NAME name...
	: $NAME contains the current state of that timeslot.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(*event[1:])
		setattr(self.parent.ctx,var,Timeslots[name].running)

class TimeslotModule(Module):
	"""\
		This module contains the generic handlers for timesloting.
		"""

	info = "Timeslot handling"

	def load(self):
		main_words.register_statement(TimeslotHandler)
		main_words.register_statement(TimeslotUpdate)
		main_words.register_statement(TimeslotStart)
		main_words.register_statement(TimeslotStop)
		main_words.register_statement(VarTimeslotHandler)
		register_condition(RunningTimeslotCheck)
		register_condition(DuringTimeslotCheck)
	
	def unload(self):
		main_words.unregister_statement(TimeslotHandler)
		main_words.unregister_statement(TimeslotUpdate)
		main_words.unregister_statement(TimeslotStart)
		main_words.unregister_statement(TimeslotStop)
		main_words.unregister_statement(VarTimeslotHandler)
		unregister_condition(RunningTimeslotCheck)
		unregister_condition(DuringTimeslotCheck)

init = TimeslotModule
