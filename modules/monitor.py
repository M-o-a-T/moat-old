#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division

"""\
This code does basic timeout handling.

monitor FOO...
	- monitors for FOO seconds

"""

from homevent.monitor import monitors, MonitorDelayFor,MonitorDelayUntil,\
	MonitorRequire,MonitorRetry,MonitorAlarm,MonitorHigh,MonitorLow,\
	MonitorLimit, MonitorDiff
from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words
from homevent.module import Module
from homevent.times import time_delta, time_until
from homevent.check import Check,register_condition,unregister_condition
import os
from twisted.python.failure import Failure
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
		monitor = monitors[tuple(event)]
		active = monitor.active
		if active:
			monitor.down()
		for p,v in self.params.iteritems():
			setattr(monitor,p,v)
		if active:
			monitor.up()

for cmd in (MonitorDelayFor,MonitorDelayUntil, MonitorRequire, \
		MonitorRetry,MonitorAlarm,MonitorHigh,MonitorLow,MonitorDiff):
	MonitorUpdate.register_statement(cmd)

class MonitorCancel(Statement):
	name = ("del","monitor")
	doc = "abort a monitor handler"
	long_doc=u"""\
del monitor ‹whatever the name is›
	This statement aborts a monitor handler.
	Everything that depended on the handler's completion will be skipped!
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: del monitor ‹name…›')
		m = monitors.pop(tuple(event))
		return m.down()

class MonitorList(Statement):
	name=("list","monitor")
	doc="list of monitoring statements"
	long_doc="""\
list monitor
	shows a list of running monitor statements.
list monitor NAME
	shows details for that monitor statement.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for m in monitors.itervalues():
				print >>self.ctx.out, " ".join(str(x) for x in m.name)
			print >>self.ctx.out, "."
		else:
			m = monitors[tuple(event)]
			print  >>self.ctx.out, "Name: "," ".join(str(x) for x in m.name)
			print  >>self.ctx.out, "Value: ",m.value
			print  >>self.ctx.out, "Up: ",("Yes" if m.active else "No")
			if not "HOMEVENT_TEST" in os.environ:
				if m.started_at:
					print  >>self.ctx.out, "Start: ",str(m.started_at)
				if m.stopped_at:
					print  >>self.ctx.out, "Stop: ",str(m.stopped_at)

			print  >>self.ctx.out, "Steps: ",m.steps,"/",m.points,"/",m.maxpoints
			if m.data:
				print  >>self.ctx.out, "Data: "," ".join(map(str,m.data))
			
			print  >>self.ctx.out, "."

class ExistsMonitorCheck(Check):
	name=("exists","monitor")
	doc="check if a monitor exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists monitor ‹name…›")
		name = tuple(args)
		return name in monitors

class RunningMonitorCheck(Check):
	name=("running","monitor")
	doc="check if a monitor is active"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if active monitor ‹name…›")
		name = tuple(args)
		return monitors[name].active


class VarMonitorHandler(Statement):
	name=("var","monitor")
	doc="assign a variable to the current value of a monitor"
	long_doc=u"""\
var monitor NAME name...
	: $NAME contains the current value of that monitor.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		w = event[:]
		var = w[0]
		name = tuple(w[1:])
		setattr(self.parent.ctx,var,monitors[name].value)


class MonitorModule(Module):
	"""\
		This module contains the generic handlers for monitoring.
		"""

	info = "Monitoring"

	def load(self):
		main_words.register_statement(MonitorUpdate)
		main_words.register_statement(MonitorCancel)
		main_words.register_statement(VarMonitorHandler)
		global_words.register_statement(MonitorList)
		register_condition(ExistsMonitorCheck)
		register_condition(RunningMonitorCheck)
	
	def unload(self):
		main_words.unregister_statement(MonitorUpdate)
		main_words.unregister_statement(MonitorCancel)
		main_words.unregister_statement(VarMonitorHandler)
		global_words.unregister_statement(MonitorList)
		unregister_condition(ExistsMonitorCheck)
		unregister_condition(RunningMonitorCheck)

init = MonitorModule
