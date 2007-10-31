#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code contains several test statements.

monitor test ...
	- a random-value monitor

"""

from homevent.statement import Statement, main_words
from homevent.event import Event
from homevent.run import process_event
from homevent.monitor import Monitor,MonitorHandler
from twisted.internet import defer

from random import Random

class Tester(Monitor):
	_min = 0
	_max = 100
	_val = None
	_step = 1
	_seed = 12345

	def __init__(self,*a,**k):
		super(Tester,self).__init__(*a,**k)
		self.rand = Random(self._seed)

	def one_value(self, step):
		if self._val is None:
			lo = self._min
			hi = self._max
		else:
			lo = max(self._min,self._val - self._step)
			hi = min(self._max,self._val + self._step)
		self._val = self.rand.randint(lo,hi)
		return defer.succeed(self._val)
		

class TestMonitor(MonitorHandler):
	name=("monitor","test")
	monitor = Tester
	doc="crete a fake sequence"
	long_doc="""\
monitor test MIN MAX STEP
	- creates a pseudo-random-valued monitor.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2 or len(event) > 3:
			raise SyntaxError("Events need at least one parameter")
		self.values["_min"] = int(event[0])
		self.values["_max"] = int(event[1])
		if len(event) > 2:
			self.values["_step"] = int(event[2])

		super(TestMonitor,self).run(ctx,**k)



from homevent.module import Module

class TestModule(Module):
	"""\
		This module contains some commands useful for testing.
		"""

	info = "Some interesting tests"

	def load(self):
		main_words.register_statement(TestMonitor)
	
	def unload(self):
		main_words.unregister_statement(TestMonitor)

init = TestModule