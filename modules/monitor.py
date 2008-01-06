# -*- coding: utf-8 -*-

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

from __future__ import division

"""\
This code does basic timeout handling.

monitor FOO...
	- monitors for FOO seconds

"""

from homevent.monitor import Monitors, MonitorDelayFor,MonitorDelayUntil,\
	MonitorRequire,MonitorRetry,MonitorAlarm,MonitorHigh,MonitorLow,\
	MonitorLimit, MonitorScale, MonitorDiff, MonitorHandler, NoWatcherError
from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words
from homevent.module import Module
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name

import os
from twisted.internet import defer

	
class MonitorUpdate(AttributedStatement):
	name = ("update","monitor")
	doc = "change the parameters of an existing monitor"
	long_doc="""\
This statement updates the parameters of an existing monitor.
"""
	def __init__(self,*a,**k):
		super(MonitorUpdate,self).__init__(*a,**k)
		self.values = {}

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) == 0:
			raise SyntaxError(u'Usage: update monitor ‹name…›')
		if not self.params:
			raise SyntaxError(u'update monitor: You did not specify any changes?')
		monitor = Monitors[Name(event)]
		active = monitor.active

		d = defer.succeed(None)
		if active:
			d.addCallback(lambda _: monitor.down())
		def setter(_):
			for p,v in self.params.iteritems():
				setattr(monitor,p,v)
		d.addCallback(setter)
		if active:
			d.addCallback(lambda _: monitor.up())
		return d

for cmd in (MonitorDelayFor, MonitorDelayUntil, MonitorRequire, \
		MonitorRetry, MonitorAlarm, MonitorLimit, MonitorScale, \
		MonitorHigh, MonitorLow, MonitorDiff):
	MonitorUpdate.register_statement(cmd)

class MonitorCancel(Statement):
	name = ("del","monitor")
	doc = "abort a monitor handler"
	long_doc=u"""\
del monitor ‹whatever the name is›
	This statement removes a monitor from the system.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: del monitor ‹name…›')
		m = Monitors.pop(Name(event))
		return m.down()

class MonitorStart(Statement):
	name = ("start","monitor")
	doc = "Start a monitor"
	long_doc=u"""\
start monitor ‹name›
	This statement starts a monitor handler.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: start monitor ‹name…›')
		m = Monitors[Name(event)]
		return m.up()

class MonitorStop(Statement):
	name = ("stop","monitor")
	doc = "Stop a monitor"
	long_doc=u"""\
stop monitor ‹name›
	This statement stops a monitor handler.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: stop monitor ‹name…›')
		m = Monitors[Name(event)]
		return m.down()

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for m in Monitors.itervalues():
				print >>self.ctx.out, " ".join(unicode(x) for x in m.name),"::",m.value,m.up_name,m.time_name
			print >>self.ctx.out, "."
		else:
			m = Monitors[Name(event)]
			print  >>self.ctx.out, "Name: "," ".join(unicode(x) for x in m.name)
			if m.params:
				print  >>self.ctx.out, "Device: "," ".join(unicode(x) for x in m.params)
			print  >>self.ctx.out, "Value: ",m.value
			print  >>self.ctx.out, "Up: ",m.up_name
			print  >>self.ctx.out, "Time: ",m.time_name
			if not "HOMEVENT_TEST" in os.environ:
				if m.started_at:
					print  >>self.ctx.out, "Start: ",unicode(m.started_at)
				if m.stopped_at:
					print  >>self.ctx.out, "Stop: ",unicode(m.stopped_at)

			print  >>self.ctx.out, "Steps: ",m.steps,"/",m.points,"/",m.maxpoints
			if m.data:
				print  >>self.ctx.out, "Data: "," ".join(unicode(x) for x in m.data)
			
			print  >>self.ctx.out, "."

class MonitorSet(Statement):
	name=("set","monitor")
	doc="feed a value to a passive monitor"
	long_doc="""\
set monitor VALUE NAME
	Sends the value to this named (passive) monitor.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u"Usage: set monitor ‹value› ‹name…›")
		m = Monitors[Name(event[1:])]
		if not m.watcher:
			raise NoWatcherError(m)
		m.watcher.callback(event[0])

class ExistsMonitorCheck(Check):
	name=("exists","monitor")
	doc="check if a monitor exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists monitor ‹name…›")
		name = Name(args)
		return name in Monitors

class RunningMonitorCheck(Check):
	name=("running","monitor")
	doc="check if a monitor is active"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if active monitor ‹name…›")
		name = Name(args)
		return Monitors[name].active


class WaitingMonitorCheck(Check):
	name=("waiting","monitor")
	doc="check if a passive monitor is requesting data"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if waiting monitor ‹name…›")
		name = Name(args)
		m = Monitors[name]
		return m.active and m.watcher is not None


class VarMonitorHandler(Statement):
	name=("var","monitor")
	doc="assign a variable to the current value of a monitor"
	long_doc=u"""\
var monitor NAME name...
	: $NAME contains the current value of that monitor.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(event[1:])
		setattr(self.parent.ctx,var,Monitors[name].value)


class MonitorModule(Module):
	"""\
		This module contains the generic handlers for monitoring.
		"""

	info = "Monitoring"

	def load(self):
		main_words.register_statement(MonitorHandler)
		main_words.register_statement(MonitorUpdate)
		main_words.register_statement(MonitorSet)
		main_words.register_statement(MonitorCancel)
		main_words.register_statement(MonitorStart)
		main_words.register_statement(MonitorStop)
		main_words.register_statement(VarMonitorHandler)
		register_condition(ExistsMonitorCheck)
		register_condition(RunningMonitorCheck)
		register_condition(WaitingMonitorCheck)
	
	def unload(self):
		main_words.unregister_statement(MonitorHandler)
		main_words.unregister_statement(MonitorUpdate)
		main_words.unregister_statement(MonitorSet)
		main_words.unregister_statement(MonitorCancel)
		main_words.unregister_statement(MonitorStart)
		main_words.unregister_statement(MonitorStop)
		main_words.unregister_statement(VarMonitorHandler)
		unregister_condition(ExistsMonitorCheck)
		unregister_condition(RunningMonitorCheck)
		unregister_condition(WaitingMonitorCheck)

init = MonitorModule
