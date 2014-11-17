# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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
This code contains the framework for watching a device.

"""

from __future__ import division,absolute_import

from homevent import TESTING
from homevent.statement import AttributedStatement, Statement
from homevent.event import Event
from homevent.run import process_event,process_failure,simple_event
from homevent.reactor import shutdown_event
from homevent.worker import ExcWorker
from homevent.times import time_delta, time_until, unixdelta, now, \
	humandelta
from homevent.base import Name,SName, SYS_PRIO
from homevent.twist import log_wait, sleepUntil, fix_exception,Jobber
from homevent.context import Context
from homevent.logging import log,TRACE,DEBUG,ERROR
from homevent.collect import Collection,Collected
from homevent.check import register_condition

from gevent.event import Event as gEvent
from gevent.queue import Channel,Queue
import gevent

from time import time
import os,sys
import datetime as dt

class Monitors(Collection):
	name = "monitor"
Monitors = Monitors()
Monitors.does("del")
register_condition(Monitors.exists)

class MonitorAgain(RuntimeError):
	"""The monitor is not ready yet; retry please"""
	pass

class MonitorError(RuntimeError):
	def __init__(self,w):
		self.monitor = w
	def __str__(self):
		return self.text % (" ".join(str(x) for x in self.monitor.name),)
	def __unicode__(self):
		return self.text % (" ".join(unicode(x) for x in self.monitor.name),)

class DupMonitorError(MonitorError):
	text = u"A monitor ‹%s› already exists"

class DupWatcherError(MonitorError):
	text = u"Already waiting for ‹%s›"

class NoWatcherError(MonitorError):
	text = u"Not waiting for ‹%s›"

class Monitor(Collected,Jobber):
	"""This is the thing that watches."""
	storage = Monitors.storage

	job = None # greenlet running the monitor loop
	running = None # Event. OFF while measuring (so that we can wait for that to end; currently used as a flag)
	passive = None # active or passive monitoring?
	send_check_event = None # send a "monitor checked"
	queue_len = 0 # length of the watch queue; 0:use a blocking channel
	watcher = None # if passive: channel for the next value
	params = None # for reporting

	delay = (1,"sec") # between two measurements at a time
	delay_for = (1,"sec") # between one set of measurements and the next one
	delay_until = () # "absolute" timespec

	steps = 0 # how many measurements have been taken
	data = () # valid values
	alarm = None # float: allowed range between one measurement and the next
	is_high = False # high alarm triggered?
	is_low = False # low alarm triggered?
	high_lim = None # alarm if above this
	high_ok_lim = None # alarm rescinded if below this
	low_lim = None # alarm if below this
	low_ok_lim = None # alarm rescinded if above this
	points = 1 # required for good value
	maxpoints = None  # max # steps
	range = None # allowed range of data within a measurement
	diff = None # required difference for a "value" event

	value = None # last correct measurement
	started_at = None # last time when measuring started or will start
	stopped_at = None # last time when measuring ended
	state_change_at = None # last time up/down got called

	def __init__(self,parent,name):
		if self.passive is None:
			self.passive = (self.__class__ is Monitor)
		if self.send_check_event is None:
			self.send_check_event = self.passive
		if self.queue_len is not None:
			if self.queue_len == 0:
				self.watcher = Channel()
			else:
				self.watcher = Queue(self.queue_len)
		self.running = gEvent()
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		super(Monitor,self).__init__(*name)

	def __repr__(self):
		if not self.job:
			act = "off"
		elif not self.running.is_set():
			act = "run "+unicode(self.steps)
		else:
			act = "on "+unicode(self.value)
			# TODO: add delay until next check
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name,act)

	def list(self):
		"""status iterator"""
		for r in super(Monitor,self).list():
			yield r
		if self.params:
			yield ("device"," ".join(unicode(x) for x in self.params))
		yield ("value",self.value)
		yield ("up",self.up_name)
		yield ("time",self.time_name)
		if not TESTING:
			if self.started_at is not None:
				yield ("start",self.started_at)
			if self.stopped_at is not None:
				yield ("stop",self.stopped_at)
			if self.state_change_at is not None:
				yield ("state change",self.state_change_at)

		yield ("steps", "%s / %s / %s" % (self.steps,self.points,self.maxpoints))
		if self.data:
			yield ("data"," ".join(unicode(x) for x in self.data))

	def update_ctx(self):
		self._ectx.value = self.value
		self._ectx.up = self.up_name
		self._ectx.time = self.time_name
		self._ectx.start_at = self.started_at
		self._ectx.stop_at = self.stopped_at
		self._ectx.change_at = self.state_change_at
		self._ectx.steps = (self.steps,self.points,self.maxpoints)
		self._ectx.data = self.data

	def info(self):
		"""list one-liner"""
		return "%s %s" % (self.up_name,self.time_name)

	@property
	def up_name(self):
		if not self.running.is_set():
			return "Run"
		elif self.job:
			return "Wait"
		else:
			return "Off"
	@property
	def time_name(self):
		if self.started_at is None:
			return "never"
		if not self.running.is_set():
			delta = now() - self.started_at
		elif self.job:
			delta = self.started_at - now()
		else:
			delta = now() - self.started_at
		delta = unixdelta(delta)
		res = humandelta(delta)

		return u"‹"+res+"›"
		# TODO: refactor that into homevent.times


	def _schedule(self):
		"""Sleep until the next time this monitor should run"""
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
		with log_wait("monitor","sleep",*self.name):
			sleepUntil(False,s)

	def filter_data(self):
		"""Discard outlier values and calculate average"""
		log("monitor",TRACE,"filter",self.data,"on", self.name)

		if len(self.data) < self.points:
			return None
		avg = sum(float(x) for x in self.data)/len(self.data)
		if not self.range:
			return avg

		data = self.data
		while True:
			lo = min(data)
			hi = max(data)
			if hi-lo <= self.range:
				return avg

			if len(data) == self.points:
				break

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
			avg = nsum/len(data)
		return None

	def _do_measure(self):
		log("monitor",TRACE,"Start run",self.name)
		try:
			self.running.clear()
			self.started_at = now()
			self._monitor()
			if self.send_check_event:
				process_event(Event(self.ectx, "monitor","checked",*self.name))
			if self.new_value is not None:
				if hasattr(self,"delta"):
					if self.value is not None:
						val = self.new_value-self.value
						self._ectx.value_delta = val
						if val >= 0 or self.delta == 0:
							process_event(Event(self.ectx,"monitor","value",self.new_value-self.value,*self.name))
							process_event(Event(self.ectx,"monitor","update",*self.name))
				else:
					process_event(Event(self.ectx,"monitor","value",self.new_value,*self.name))
					process_event(Event(self.ectx,"monitor","update",*self.name))
			if self.new_value is not None:
				self.value = self.new_value
		except Exception as e:
			fix_exception(e)
			process_failure(e)
		finally:
			log("monitor",TRACE,"Stop run",self.name)
			self.running.set()
			self._schedule()

	def _run_loop(self):
		"""Main monitor loop."""
		while True:
			self._do_measure()
			self._schedule()

	def _monitor(self):
		"""This implements a monitor sequence."""
		self.steps = 0
		self.data = []
		self.new_value = None

		def delay():
			if isinstance(self.delay,tuple):
				sleepUntil(False,time_delta(self.delay))
			else:
				sleepUntil(False,self.delay)

		try:
			while self.job and (self.maxpoints is None or self.steps < self.maxpoints):
				if self.steps and not self.passive:
					delay()

				self.steps += 1

				try:
					val = self.one_value(self.steps)

				except MonitorAgain:
					pass

				except Exception as e:
					fix_exception(e)
					process_failure(e)
					break

				else:
					try:
						val = float(val)
					except (TypeError,ValueError):
						log("monitor",ERROR,self.name,"not a float:",val)
						continue
					if hasattr(self,"factor"):
						try:
							val = val * self.factor + self.offset
						except (TypeError,ValueError) as e:
							log("monitor",ERROR,self.name,val,self.factor,self.offset)
							continue
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
									process_event(Event(self.ectx,"monitor","alarm",avg,*self.name))
									process_event(Event(self.ectx,"monitor","jump",*self.name))
							except Exception as e:
								fix_exception(e)
								process_failure(e)
							else:
								self.new_value = avg
						return
					else:
						log("monitor",TRACE,"More data", self.data, "for", u"‹"+" ".join(unicode(x) for x in self.name)+u"›")
				
			try:
				process_event(Event(self.ectx,"monitor","error",*self.name))
			except Exception as e:
				fix_exception(e)
				process_failure(e)

		finally:
			log("monitor",TRACE,"End run", self.name)
			self.stopped_at = now()


	def one_value(self, step):
		"""\
			Get one value from some "set monitor" command.
			Override this for active monitoring.
			"""
		if self.send_check_event and step==1:
			process_event(Event(self.ectx, "monitor","checking",*self.name))

		with log_wait("monitor","one_value",*self.name):
			return self.watcher.get(block=True, timeout=None)

	def up(self):
		with log_wait("monitor up "+repr(self)):
			while self.job and self.job.dead:
				gevent.sleep(0.1) # link will clear

		if not self.job:
			self.value = None
			simple_event("monitor","start",*self.name)
			self.start_job("job",self._run_loop)
			self.state_change_at = now()

			def tell_ended(_):
				simple_event("monitor","stop",*self.name)
			self.job.link(tell_ended)

	def delete(self,ctx=None):
		self.down()
		super(Monitor,self).delete()

	def down(self):
		self.state_change_at = now()
		self.stop_job("job")

monitor_nr = 0
	
class MonitorHandler(AttributedStatement):
	name="monitor passive"
	doc="A monitor which waits for values"
	long_doc="""\
monitor passive
	- Handle monitoring by explicit "set" commands.
	"""

	monitor = Monitor
	stopped = False

	def __init__(self,*a,**k):
		self.passive = (self.monitor is Monitor)

		super(MonitorHandler,self).__init__(*a,**k)

		global monitor_nr
		monitor_nr += 1
		self.nr = monitor_nr
		self.displayname=Name("_monitor",self.nr)

		self.values = {}

	def run(self,ctx,**k):
		m = self.monitor(self, self.displayname)
		for p,v in self.values.iteritems():
			setattr(m,p,v)
		if m.params is None:
			m.params = ("passive",) if self.passive else ("unknown",)
		if not self.stopped:
			return m.up()

	
class MonitorName(Statement):
	name = "name"
	doc = "name a Monitor handler"
	long_doc=u"""\
name ‹whatever you want›
	This statement assigns a name to a Monitor statement.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: name ‹name…›')
		self.parent.displayname = SName(event)
MonitorHandler.register_statement(MonitorName)


class MonitorDelayFor(Statement):
	name = "delay for"
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
	name = "delay until"
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
	name = "require"
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
			self.parent.values["points"] = None
		else:
			try:
				val = int(event[0])
				if val <= 0:
					raise ValueError
				self.parent.values["points"] = val
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: require: ‹num› needs to be a positive integer')
		if event[1] == "*":
			self.parent.values["range"] = None
		else:
			try:
				val = float(event[1])
				if val < 0:
					raise ValueError
				self.parent.values["range"] = val
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: require: ‹range› needs to be a non-negative number')
MonitorHandler.register_statement(MonitorRequire)


class MonitorRetry(Statement):
	name = "retry"
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
			except (ValueError,TypeError):
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
				except (ValueError,TypeError):
					raise SyntaxError(u'Usage: retry: ‹delay› needs to be a positive number or timepec')
		elif len(event) > 2:
			self.parent.values["delay"] = tuple(event[1:]) # assume a timespec
MonitorHandler.register_statement(MonitorRetry)


class MonitorAlarm(Statement):
	name = "alarm"
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
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: alarm: ‹range› needs to be a positive number')
MonitorHandler.register_statement(MonitorAlarm)


class MonitorDiff(Statement):
	name = "diff"
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
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: diff: ‹amount› needs to be a non-negative number')
MonitorHandler.register_statement(MonitorDiff)


class MonitorHigh(Statement):
	name = "high"
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
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: high: ‹value› needs to be a number')
		if len(event) == 2:
			try:
				val = float(event[1])
				if val > self.parent.values["high"]:
					raise SyntaxError(u'Usage: high: ‹ok_value› needs to be smaller than ‹value›')
				self.parent.values["ok_high"] = val

			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: high: ‹ok_value› needs to be a number')
		else:
			self.parent.values["ok_high"] = None
MonitorHandler.register_statement(MonitorHigh)


class MonitorLow(Statement):
	name = "low"
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
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: low: ‹value› needs to be a number')
		if len(event) == 2:
			try:
				val = float(event[1])
				if val > self.parent.values["low"]:
					raise SyntaxError(u'Usage: low: ‹ok_value› needs to be greater than ‹value›')
				self.parent.values["ok_low"] = val

			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: low: ‹ok_value› needs to be a number')
		else:
			self.parent.values["ok_low"] = None
MonitorHandler.register_statement(MonitorLow)



class MonitorLimit(Statement):
	name = "limit"
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
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: limit: ‹low› needs to be a number or ‹*›')
		if event[1] == "*":
			self.parent.limit_high = "*"
		else:
			try:
				self.parent.values["limit_high"] = hi = float(event[1])
			except (ValueError,TypeError):
				raise SyntaxError(u'Usage: limit: ‹high› needs to be a number or ‹*›')
		if lo is not None and hi is not None and lo >= hi:
			raise SyntaxError(u'Usage: limit: ‹low› needs to be greater than ‹high›')
MonitorHandler.register_statement(MonitorLimit)


class MonitorScale(Statement):
	name = "scale"
	doc = "adapt values"
	long_doc=u"""\
scale ‹factor› ‹offset›
	Adjust raw measurements by first multiplying by ‹factor›,
	then adding ‹offset›.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) != 2:
			raise SyntaxError(u'Usage: scale ‹factor› ‹offset›')

		if event[0] == "*":
			self.parent.values["factor"] = 1
		else:
			self.parent.values["factor"] = float(event[0])

		if event[1] == "*":
			self.parent.values["offset"] = 0
		else:
			self.parent.values["offset"] = float(event[1])
MonitorHandler.register_statement(MonitorScale)


class MonitorDelta(Statement):
	name = "delta"
	doc = "report difference"
	long_doc=u"""\
delta
	Report the difference between the old and new values.
delta up
	Same, but assume that the value only increases.
	Used for counters.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 0:
			self.parent.values["delta"] = 0
		elif len(event) == 1 and event[0] == "up":
			self.parent.values["delta"] = 1
		else:
			raise SyntaxError(u'Usage: delta [up]')
MonitorHandler.register_statement(MonitorDelta)


class MonitorStopped(Statement):
	name = "stopped"
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
MonitorHandler.register_statement(MonitorStopped)

