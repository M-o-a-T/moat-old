#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division

"""\
This code contains the framework for watching a device.

"""

from homevent.statement import AttributedStatement, Statement
from homevent.event import Event
from homevent.run import process_event,process_failure,register_worker
from homevent.reactor import shutdown_event
from homevent.module import Module
from homevent.worker import ExcWorker
from homevent.times import time_delta, time_until, unixdelta, now
from homevent.constants import SYS_PRIO
from homevent.twist import deferToLater
from homevent.context import Context
from homevent.logging import log,TRACE

from time import time
import os,sys
from twisted.python.failure import Failure
from twisted.internet import reactor,defer
import datetime as dt

monitors = {}

class MonitorError(RuntimeError):
    def __init__(self,w):
        self.monitor = w
    def __str__(self):
        return self.text % (" ".join(str(x) for x in self.monitor.name),)

#class WaitLocked(WaitError):
#    text = u"Tried to process waiter ‹%s› while it was locked"
#
#class WaitCancelled(WaitError):
#    """An error signalling that a wait was killed."""
#    text = u"Waiter ‹%s› was cancelled"

class DupMonitorError(MonitorError):
    text = u"A monitor ‹%s› already exists"

class Monitor(object):
	"""This is the thing that watches."""
	active = False # enabled?
	running = None # Deferred while measuring
	timer = None # callLater() timer
	timerd = None # deferred triggered by the timer

	delay = (1,"sec") # between two measurements at a time
	delay_for = (1,"sec") # between one set of measurements and the next one
	delay_until = () # "absolute" timespec

	step = 0 # how many measurements have been taken
	data = () # valid values
	alarm = None # float: allowed range between one measurement and the next
	is_high = False # high alarm triggered?
	is_low = False # low alarm triggered?
	high_lim = None # alarm if above this
	high_ok_lim = None # alarm rescinded if below this
	low_lim = None # alarm if below this
	low_ok_lim = None # alarm rescinded if above this
	points = 1 # required for good value
	maxpoints = 1  # max # steps
	range = None # allowed range of data within a measurement
	diff = None # required difference for a "value" event

	name = None # my name
	value = None # last correct measurement
	started_at = None # last time when measuring started or will start
	stopped_at = None # last time when measuring ended

	def __init__(self,parent,name):

		self.ctx = parent.ctx
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		self.name = name
		if self.name in monitors:
			raise DupMonitorError(self)

		monitors[self.name] = self

	def __repr__(self):
		if self.active:
			act = "running "+str(self.value)
			# TODO: add delay until next check
		else:
			act = "off"
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name,act)

	def _schedule(self):
		if self.running or not self.active: return
		if self.timer:
			self.timer.cancel()
			self.timer = None

		s = self.stopped_at or now()
		if self.delay_for:
			if isinstance(self.delay_for,tuple):
				s = time_delta(self.delay_for, now=s)
			else:
				s += dt.timedelta(0,self.delay_for)
		if self.delay_until:
			if self.stopped_at:
				s = time_until(self.delay_until, now=s, invert=True)
			s = time_until(self.delay_until, now=s)
		if not self.delay_for and not self.delay_until:
			if isinstance(self.delay,tuple):
				s = time_delta(self.delay, now=s)
			else:
				s += dt.timedelta(0,self.delay)

		self.started_at = s
		self.timer = reactor.callLater(unixdelta(s-now()), self._run)

	def filter_data(self):
		log(TRACE,"filter",self.data,"on",self.name)

		if len(self.data) < self.points:
			return None
		avg = sum(self.data)/len(self.data)
		if not self.range:
			return avg

		data = self.data
		while True:
			lo = min(self.data)
			hi = max(self.data)
			if hi-lo <= self.range:
				return avg
			if len(data) == self.points: break

			new_data = []
			extr = None # stored outlier
			nsum = 0 # new sum
			dif = None # difference for extr
			for val in data:
				ndif = abs(avg-val)
				if dif is None or dif < ndif:
					dif = ndif
					if extr is not None:
						nsum += extr
						new_data.append(extr)
					extr = val
				else:
					nsum += val
					new_data.append(val)
			data = new_data
			avg = sum/len(data)
		return None

	def _run(self):
		self.timer = None
		assert not self.running,"Concurrent calls"
		self.running = self._run_me()
		self.running.addErrback(process_failure)
		log(TRACE,"Start run",self.name)
	@defer.inlineCallbacks
	def _run_me(self):
		self.steps = 0
		self.data = []

		def delay():
			assert not self.timer,"No timer set"
			self.timerd = defer.Deferred()
			def kick():
				d = self.timerd
				self.timerd = None
				self.timer = None
				d.callback(None)
			if isinstance(self.delay,tuple):
				self.timer = reactor.callLater(unixdelta(time_delta(self.delay)-now()), kick)
			else:
				self.timer = reactor.callLater(self.delay, kick)

		try:
			while self.steps < self.maxpoints:
				if not self.active:
					return
				if self.steps:
					yield delay()
				self.steps += 1
				try:
					val = yield self.one_value()
		
				except Exception,e:
					self.active = False
					yield process_failure()

				else:
					self.data.append(val)

					avg = self.filter_data()
					if avg is not None:
						if self.value is None or \
								self.diff is None or \
								abs(self.value-avg) > self.diff:

							try:
								if self.value is not None and \
										self.alarm is not None and \
										abs(self.value-avg) > self.alarm:
									yield process_event(Event(Context(),"monitor","alarm",avg,*self.name))
								yield process_event(Event(Context(),"monitor","value",avg,*self.name))
							except Exception,e:
								yield process_failure()
							else:
								self.value = avg
						return
				
			self.active = False
		
			try:
				yield process_event(Event(Context(),"monitor","error",*self.name), return_errors=True)
			except Exception,e:
				yield process_failure()

		finally:
			log(TRACE,"End run",self.name)
			self.running = None
			self.stopped_at = now()
			self._schedule()


	def one_value(self):
		"""\
			The main code. It needs to get one value from the remote side
			by returning a Deferred.
			"""
		return defer.fail(Failure(AssertionError("%s: You need to override one_value()" % (self.__class__.__name__,))))

	def up(self):
		if not self.active:
			self.active = True
			deferToLater(self._run)

	def down(self):
		d = defer.Deferred()
		if self.active:
			self.active = False
			if self.timer:
				self.timer.cancel()
				self.timer = None
			e = self.timerd
			if e:
				self.timerd = None
				e.callback(None)
			if self.running:
				def trigger(_):
					d.callback(None)
					return _
				self.running.addBoth(trigger)
			else:
				d.callback(None)
		else:
			d.callback(None)
		return d


monitor_nr = 0
	
class MonitorHandler(AttributedStatement):
	name=("monitor","whatever")
	doc="Bad boy/girl! Don't register this statement!"
	long_doc="""\
monitor whatever
	- programmer error!
	  The MonitorHandler needs to be subclassed. Don't register!
	"""

	monitor = Monitor
	stopped = False

	def __init__(self,*a,**k):
		if self.monitor is Monitor:
			raise NotImplementedError("Need to assign a subclass to .monitor!")

		super(MonitorHandler,self).__init__(*a,**k)

		global monitor_nr
		monitor_nr += 1
		self.nr = monitor_nr
		self.displayname=("_monitor",self.nr)

		self.values = {}

	def run(self,ctx,**k):
		m = self.monitor(self, self.displayname)
		for p,v in self.values.iteritems():
			setattr(m,p,v)
		if not self.stopped:
			return m.up()

	
class MonitorName(Statement):
	name = ("name",)
	doc = "name a Monitor handler"
	long_doc=u"""\
name ‹whatever you want›
	This statement assigns a name to a Monitor statement.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: name ‹name…›')
		self.parent.displayname = tuple(event)
MonitorHandler.register_statement(MonitorName)


class MonitorDelayFor(Statement):
	name = ("delay","for")
	doc = "Interval between measurements"
	long_doc=u"""\
delay for ‹time interval›
	Set the minimum time between two measurements.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: delay for *|‹timespec›')
		elif len(event) == 1:
			if event[0] == "*":
				self.parent.values['delay_for'] = None
			else:
				self.parent.values['delay_for'] = float(event[0])
		else:
			self.parent.values['delay_for'] = tuple(event)
MonitorHandler.register_statement(MonitorDelayFor)


class MonitorDelayUntil(Statement):
	name = ("delay","until")
	doc = "Time for measurements"
	long_doc=u"""\
delay until ‹time interval›
	Set the time when the first/next measurement happens.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: delay until *|‹timespec›')
		elif len(event) == 1 and event[0] == "*":
			self.parent.values['delay_until'] = None
		else:
			self.parent.values['delay_until'] = tuple(event)
MonitorHandler.register_statement(MonitorDelayUntil)


class MonitorRequire(Statement):
	name = ("require",)
	doc = "Interval for valid measurements"
	long_doc=u"""\
require ‹num› ‹range›
	Specify the number of measurements which need to be within a given
	range for the read-out to be valid.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError(u'Usage: require ‹num› ‹range›')
		if event[0] == "*":
			self.parent.values["point"] = None
		else:
			try:
				val = int(event[0])
				if val <= 0:
					raise ValueError
				self.parent.values["point"] = val
			except ValueError:
				raise SyntaxError(u'Usage: require: ‹num› needs to be a positive integer')
		if event[1] == "*":
			self.parent.values["range"] = None
		else:
			try:
				val = float(events[1])
				if val < 0:
					raise ValueError
				self.parent.values["range"] = val
			except ValueError:
				raise SyntaxError(u'Usage: require: ‹range› needs to be a non-negative number')
MonitorHandler.register_statement(MonitorRequire)


class MonitorRetry(Statement):
	name = ("retry",)
	doc = "Number of valid measurements"
	long_doc=u"""\
retry ‹num› ‹delay›
	Specify the number of measurements that will be taken, as well as
	the delay between them.
	Monitoring will stop with an error if unsuccessful after that many
	retries.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u'Usage: retry ‹num› ‹delay›')
		if event[0] == "*":
			self.parent.values["maxpoints"] = None
		else:
			try:
				val = int(event[0])
				if val <= 0:
					raise ValueError
				self.parent.values["maxpoints"] = val
			except ValueError:
				raise SyntaxError(u'Usage: retry: ‹num› needs to be a positive integer')

		if len(event) == 2:
			if len(event) > 2:
				self.parent.values["delay"] = tuple(event[1:])
			elif event[1] == "*":
				self.parent.values["delay"] = None
			else:
				try:
					val = float(event[1:])
					if self.parent.delay <= 0:
						raise ValueError
					self.parent.values["delay"] = val
				except ValueError:
					raise SyntaxError(u'Usage: retry: ‹delay› needs to be a positive number or timepec')
		elif len(event) > 2:
			self.parent.values["delay"] = tuple(event[1:]) # assume a timespec
MonitorHandler.register_statement(MonitorRetry)


class MonitorAlarm(Statement):
	name = ("alarm",)
	doc = "Range of permissible change"
	long_doc=u"""\
alarm ‹range›
	Specify the allowable difference between the last measurement and
	the current one. Exceeding it will trigger an alarm event.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: alarm ‹range›')
		if event[0] == "*":
			self.parent.values["alarm"] = None
		else:
			try:
				val = float(event[0])
				if val <= 0:
					raise ValueError
				self.parent.values["alarm"] = val
			except ValueError:
				raise SyntaxError(u'Usage: alarm: ‹range› needs to be a positive number')
MonitorHandler.register_statement(MonitorAlarm)


class MonitorDiff(Statement):
	name = ("diff",)
	doc = "Minimum change for a new event to be triggered"
	long_doc=u"""\
diff ‹amount›
	If the measured value does not change by more than the given amount,
	no event will be generated.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: diff ‹amount›')
		if event[0] == "*":
			self.parent.values["diff"] = None
		else:
			try:
				val = float(event[0])
				if val < 0:
					raise ValueError
				self.parent.values["diff"] = val
			except ValueError:
				raise SyntaxError(u'Usage: diff: ‹amount› needs to be a non-negative number')
MonitorHandler.register_statement(MonitorDiff)


class MonitorHigh(Statement):
	name = ("high",)
	doc = "Upper alarm threshold"
	long_doc=u"""\
high ‹value› [‹ok_value›]
	If a measurement exceeds the ‹value›, an event will be triggered.
	Another event will be triggered when the measurement falls below the
	‹ok_value› (which defaults to ‹value›).
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1 and len(event) != 2 \
				or len(event) == 2 and event[0] == "*":
			raise SyntaxError(u'Usage: high ‹value› [‹ok_value›]')
		if event[0] == "*":
			self.parent.values["high"] = None
		else:
			try:
				self.parent.values["high"] = float(event[0])
			except ValueError:
				raise SyntaxError(u'Usage: high: ‹value› needs to be a number')
		if len(event) == 2:
			try:
				val = float(event[1])
				if val > self.parent.values["high"]:
					raise SyntaxError(u'Usage: high: ‹ok_value› needs to be smaller than ‹value›')
				self.parent.values["ok_high"] = val

			except ValueError:
				raise SyntaxError(u'Usage: high: ‹ok_value› needs to be a number')
		else:
			self.parent.values["ok_high"] = None
MonitorHandler.register_statement(MonitorHigh)


class MonitorLow(Statement):
	name = ("low",)
	doc = "Lower alarm threshold"
	long_doc=u"""\
low ‹value› [‹ok_value›]
	If a measurement falls below the ‹value›, an event will be triggered.
	Another event will be triggered when the measurement exceeds the
	‹ok_value› (which defaults to ‹value›).
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1 and len(event) != 2 \
				or len(event) == 2 and event[0] == "*":
			raise SyntaxError(u'Usage: low ‹value› [‹ok_value›]')
		if event[0] == "*":
			self.parent.values["low"] = None
		else:
			try:
				self.parent.values["low"] = float(event[0])
			except ValueError:
				raise SyntaxError(u'Usage: low: ‹value› needs to be a number')
		if len(event) == 2:
			try:
				val = float(event[1])
				if val > self.parent.values["low"]:
					raise SyntaxError(u'Usage: low: ‹ok_value› needs to be greater than ‹value›')
				self.parent.values["ok_low"] = val

			except ValueError:
				raise SyntaxError(u'Usage: low: ‹ok_value› needs to be a number')
		else:
			self.parent.values["ok_low"] = None
MonitorHandler.register_statement(MonitorLow)



class MonitorLimit(Statement):
	name = ("limit",)
	doc = "permissible range"
	long_doc=u"""\
limit ‹low› ‹high›
	Measurements must be between ‹low› and ‹high›.
	If not, monitoring will be disabled and an error event will trigger.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) != 2:
			raise SyntaxError(u'Usage: limit ‹low› ‹high›')

		if event[0] == "*":
			self.parent.values["limit_low"] = "*"
		else:
			try:
				self.parent.values["limit_low"] = lo = float(event[0])
			except ValueError:
				raise SyntaxError(u'Usage: limit: ‹low› needs to be a number or ‹*›')
		if event[1] == "*":
			self.parent.limit_high = "*"
		else:
			try:
				self.parent.values["limit_high"] = hi = float(event[1])
			except ValueError:
				raise SyntaxError(u'Usage: limit: ‹high› needs to be a number or ‹*›')
		if lo is not None and hi is not None and lo >= hi:
			raise SyntaxError(u'Usage: limit: ‹low› needs to be greater than ‹high›')
MonitorHandler.register_statement(MonitorLimit)


class MonitorStopped(Statement):
	name = ("stopped",)
	doc = "start disabled"
	long_doc=u"""\
stopped
	Do not start the monitor immediately;
	instead, wait for a ‹start monitor› command.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u'Usage: stopped')
		self.parent.stopped = True


class Shutdown_Worker_Monitor(ExcWorker):
    """\
        This worker kills off all monitors.
        """
    prio = SYS_PRIO+3

    def does_event(self,ev):
        return (ev is shutdown_event)
    def process(self,queue,*a,**k):
        d = defer.succeed(None)
        for m in monitors.values():
            def tilt(_,monitor):
                return monitor.down()
            d.addBoth(tilt,m)
        return d

    def report(self,*a,**k):
        return ()


register_worker(Shutdown_Worker_Monitor("Monitor killer"))
