# -*- coding: utf-8 -*-
##BP
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
from __future__ import division,absolute_import

"""\
This code contains several test statements.

monitor test ...
	- a random-value monitor

"""

import six

from moat.statement import Statement, main_words
from moat.event import Event
from moat.run import simple_event
from moat.monitor import Monitor,MonitorHandler
from moat.in_out import register_input,register_output, unregister_input,unregister_output, Input,Output
from weakref import WeakValueDictionary
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
		return self._val
		

class TestMonitor(MonitorHandler):
	name="monitor test"
	monitor = Tester
	doc="create a fake sequence"
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
		self.values["params"] = ("test",six.text_type(event[0])+u"…"+six.text_type(event[1]))
		if len(event) > 2:
			self.values["_step"] = int(event[2])

		super(TestMonitor,self).run(ctx,**k)


ins = WeakValueDictionary()
class FakeInput(Input):
	typ="fake"
	value = None
	doc="An input which is set by the corresponding output"
	def __init__(self,*a,**k):
		super(FakeInput,self).__init__(*a,**k)
		ins[self.name]=self

	def list(self):
		for r in super(FakeInput,self).list():
			yield r
		if self.value is not None:
			yield ("value",self.value)

	def _read(self):
		return self.value
	
class FakeOutput(Output):
	typ="fake"
	doc="An output that sets the input with the same name"
	def _write(self,val):
		old_val = ins[self.name].value
		ins[self.name].value = val
		simple_event("input","change",*self.name, value=val, last_value=old_val, fake=True)


from moat.module import Module

class TestModule(Module):
	"""\
		This module contains some commands useful for testing.
		"""

	info = "Some interesting tests"

	def load(self):
		main_words.register_statement(TestMonitor)
		register_input(FakeInput)
		register_output(FakeOutput)
	
	def unload(self):
		main_words.unregister_statement(TestMonitor)
		unregister_input(FakeInput)
		unregister_output(FakeOutput)

init = TestModule
