# -*- coding: utf-8 -*-

##
##  Copyright © 2012, Matthias Urlichs <matthias@urlichs.de>
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
This is the core of external input and output.

"""

from homevent.statement import Statement, main_words, AttributedStatement,WordAttached
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name,SName
from homevent.collect import Collection,Collected
from homevent.twist import fix_exception,reraise,Jobber,callLater
from homevent.times import humandelta,now,unixtime
from homevent.run import simple_event,process_failure
from homevent.context import Context
from homevent.check import register_condition

from homevent.delay import DelayFor,DelayWhile,DelayUntil,DelayNext

import os
import sys
import socket
import errno

class Inputs(Collection):
	name = "input"
Inputs = Inputs()
Inputs.does("del")
register_condition(Inputs.exists)

class Outputs(Collection):
	name = "output"
Outputs = Outputs()
Outputs.does("del")
register_condition(Outputs.exists)

class BadValue(RuntimeError):
	"""The input doesn't match the expected values"""
	def __init__(self, inp,val):
		self.inp = inp
		self.val = val
	def __str__(self):
		return "BadValue: read %s: bad value for %s" % (self.val,self.inp)
	

inputmakers = {}
outputmakers = {}
def _register(store,io,what):
	if io.typ in store:
		raise ValueError("An %sput handler for '%s' is already registered." % \
			(what,io.typ))
	store[io.typ] = io
def _unregister(store,io,what):
	if io.typ not in store:
		raise ValueError("No %sput handler for '%s' is registered." % \
			(what,io.typ))
	del store[io.typ]

def register_input(inp):
	_register(inputmakers,inp,"in")
	return inp
def unregister_input(inp):
	_unregister(inputmakers,inp,"in")
def register_output(outp):
	_register(outputmakers,outp,"out")
	return outp
def unregister_output(outp):
	_unregister(outputmakers,outp,"out")


class CommonIO(Collected):
	"""This class collects common code for input and output"""
	typ = "???"
	doc = "you forgot to document this"
	long_doc = None

	params = () # creation parameters
	addons = {} # data from additional commands
	ranges = () # tuples of allowed values
	values = () # additional allowed values

	def __init__(self, name, params,addons,ranges,values):
		self.name = name
		self.params = params
		self.ranges = ranges
		self.values = values
		self.addons = addons

		super(CommonIO,self).__init__()

	def info(self):
		return "%s %s:%s" % (self.typ, self.name, self.last_value)
			
	def list(self):
		for r in super(CommonIO,self).list():
			yield r
		yield ("type",self.typ)
		for r in self.ranges:
			yield ("allowed range", u"%s … %s" % (r[0] if r[0] is not None else u"-∞", r[1] if r[1] is not None else u"∞", ))
		for r in self.values:
			yield ("allowed value",r)

	def repr(self, res):
		"""Represent the input, i.e. translate input values to script data"""
		# also needed for output
		return res

	def _read(self):
		"""Read an external's value. Override this."""
		raise NotImplementedError("You need to override %s._read()" % (self.__class__.__name__,))

	def read(self):
		"""Read an output, check range."""
		res = self._read()
		res = self.repr(res)
		self.check(res)
		self.last_time = now()
		self.last_value = res
		return res


	def check(self,res):
		"""\
			Check whether a value is accepted.
			Otherwise, throws BadValue.

			This checks the script values.
			"""
		if res in self.values:
			return
		if not self.ranges:
			return
		for a,b in self.ranges:
			try:
				if a is not None and res < a:
					continue
				if b is not None and b < res:
					continue
				return
			except TypeError: # py3 does this, sensibly
				pass
		raise BadValue(self.name, res)


class Input(CommonIO):
	"""This represents a single input."""
	storage = Inputs
	last_value = None

	typ = "???input"

	def list(self):
		for r in super(Input,self).list():
			yield r
		if self.last_value is not None:
			yield ("last read", self.last_time)
			yield ("last value",self.last_value)


class OutTimers(Collection):
	name = "outtimer"
OutTimers = OutTimers()
OutTimers.does("del")
register_condition(OutTimers.exists)
tseq=0

class OutTimer(Collected):
	"""Timer for timed outputs"""
	storage = OutTimers

	_timer = None
	def __init__(self,parent,timer,nextval):
		global tseq
		tseq += 1
		self.name = self.parent.name+(str(tseq),)
		super(OutTimer,self).__init__()
		self.parent = parent
		self.timer = timer
		self.val = nextval
		self.q = AsyncResult()
		self._start()

	def info(self):
		return "%s %s:%s" % (self.typ, self.name, self.last_value)

	def list(self):
		n = now()
		for r in super(OutTimer,self).list():
			yield r
		yield ("output",self.parent.name)
		yield ("start", self.started)
		yield ("end", self.timer)
		yield ("next value",self.val)

	def _start(self):
		if self._timer:
			self._timer.cancel()
		self.started = now()
		self._timer = callLater(False,self.timer,self._timeout)
	
	def _timeout(self):
		self._timer = None
		try:
			self.parent.set(self.val)
		except Exception as ex:
			fix_exception(ex)
			self.q.set(ex)
		else:
			self.q.set(None)
	
	def done(self):
		"""called externally via _tmwrite() when the external timer ends"""
		if self._timer:
			self._timer.cancel()
			self._timer = None
		if not self.q.ready():
			self.q.set(None)

	def cancel(self):
		self.delete()

	def delete(self):
		if self._timer is not None:
			self._timer.cancel()
			self._timer = None
		self.q.set(DelayCancelled(self))

		self.delete_done()
	


class Output(CommonIO):
	"""This represents a single output."""
	storage = Outputs
	last_value = None
	timer = None
	timing = OutTimer
	_tmwrite = None

	typ = "???output"

	def list(self):
		for r in super(Output,self).list():
			yield r
		if self.last_value is not None:
			yield ("last write", self.last_time)
			yield ("last value",self.last_value)

	def _write(self,val):
		"""Write an output. Override this."""
		raise NotImplementedError("You need to override %s._write()" % (self.__class__.__name__,))

	def write(self,val, timer=None,nextval=None,async=False):
		"""Read an input, check range."""
		self.check(val)
		if nextval is not None:
			self.check(nextval)
			wnextval = self.trans(nextval)
		else:
			wnextval = None
		wval = self.trans(val)
		if self.timer is not None and (self.last_value != wval or timer is not None):
			self.timer.cancel()
			self.timer = None

		if self.last_value != wval:
			simple_event(Context(),"output","set",self.repr(self.last_value),self.repr(wval),*self.name)

		self.last_value = wval
		self.last_time = now()

		if timer is None:
			self._write(wval)
		else:
			simple_event(Context(),"output","set",self.repr(wval),self.repr(wnextval),*self.name)
			if self._tmwrite is not None:
				self._tmwrite(wval,timer,wnextval)
			else:
				self._write(wval)
			self.timer = self.timing(self,timer,nextval)
			if async:
				gevent.spawn(self._rewrite_ex,wval,wnextval)
			else:
				self._rewrite(wval,wnextval)

	def _rewrite_ex(self,wval,wnextval):
		try:
			_rewrite_ex(wval,wnextval)
		except Exception as ex:
			fix_exception(ex)
			process_failure(ex)

	def _rewrite(self,wval,wnextval):
		res = self.timer.q.get()
		if isinstance(res,BaseException):
			reraise(res)
		simple_event(Context(),"output","set",self.repr(wval),self.repr(wnextval),*self.name)


	def trans(self, val):
		"""Translate the output, i.e. script data to input values"""
		return val


class MakeIO(AttributedStatement):
	"""Common base class for input and output creation statements"""
	ranges = None
	values = None
	addons = None

	registry = None # override in subclass
	dest = None

	def __init__(self,*a,**k):
		super(MakeIO,self).__init__(*a,**k)
		self.ranges = []
		self.values = []
		self.addons = {}

	def run(self,ctx,**k):
		event = self.params(ctx)
		if self.dest is None:
			if len(event) < 2:
				raise SyntaxError(u'Usage: %s ‹name› ‹typ› ‹params›'%(self.name,))
			self.dest = Name(event[0])
			typ = event[1]
			d = 2
		else:
			if len(event) < 1:
				raise SyntaxError(u'Usage: %s ‹typ› ‹params›'%(self.name,))
			typ = event[0]
			d = 1

		self.registry[typ](self.dest.apply(ctx), event.apply(ctx,drop=d), self.addons,self.ranges,self.values)


# the first version was to be directly attached to variables, but that doesn't work
#class BoolIO(WordAttached):
class BoolIO(object):
	"""A boolean mix-in. Add *before* Input or Output class."""
	bools = ("off","on")
	def __init__(self,name, params,addons,ranges=(),values=()):
		if addons and "bools" in addons:
			self.bools = addons['bools']

		super(BoolIO,self).__init__(name, params,addons, ranges,tuple(values)+(False,True,"on","off","False","True",0,1,"0","1"))

	def trans(self,res):
		res = str(res).lower()
		if res in ("on","true","1",self.bools[1]):
			return True
		if res in ("off","false","0",self.bools[0]):
			return False
		raise BadValue(self.name, res)

	def repr(self,res):
		return self.bools[bool(res)]

	
#@BoolIO.register_statement
@MakeIO.register_statement
class BoolParams(Statement):
	name="bool"
	doc="specify the names for 'on' and 'off'"

	long_doc = u"""\
bool ‹yes› ‹no›
  - For boolean I/O, specify which names to use for signals that are turned on, or off.
    Surprisingly, the defaults are 'on' and 'off'.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError(u"Usage: bool ‹yes› ‹no›")
		self.parent.addons['bools'] = (event[1],event[0])


@main_words.register_statement
class MakeInput(MakeIO):
	name="input"
	storage = Inputs
	registry = inputmakers

	doc="create an input"
	long_doc="""\
input ‹name› ‹type› ‹params…›
  - declare an input of the specified type, with parameters.
    See the input classes' help text for specific parameter values.
input ‹type› ‹params…› :name ‹name…› 
  - same as above, but use a multi-word name.
"""


@main_words.register_statement
class MakeOutput(MakeIO):
	name="output"
	storage = Outputs
	registry = outputmakers

	doc="create an output"
	long_doc="""\
output ‹name› ‹type› ‹params…›
  - declare an output of the specified type, with parameters.
    See the output classes' help text for specific parameter values.
output ‹type› ‹params…› :name ‹name…› 
  - same as above, but use a multi-word name.
"""



@MakeIO.register_statement
class IOName(Statement):
	name="name"
	dest = None
	doc="specify the name of this port"

	long_doc = u"""\
name ‹name…›
  - Use this form for ports with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)

@MakeIO.register_statement
class IORange(Statement):
	name="range"
	doc="specify boundaries for values"

	long_doc = u"""\
range ‹from› ‹to›
  - Tell this input that it accepts this range.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			 raise SyntaxError(u'Usage: range ‹low› ‹high›')
		try:
			a = int(event[0]) if event[0] != "" else None
			b = int(event[1]) if event[1] != "" else None
		except ValueError:
			a = float(event[0]) if event[0] != "" else None
			b = float(event[1]) if event[1] != "" else None
		self.parent.ranges.append((a,b))

@MakeIO.register_statement
class IOValue(Statement):
	name="value"
	doc="specify single allowed values"

	long_doc = u"""\
value ‹val›…
  - Tell this input that it accepts this particular value.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			 raise SyntaxError(u'Usage: value ‹val›…')
		self.parent.values.extend(event)


class IOvar(Statement):
	"""base class for input and output variables"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError("Usage: %s NAME INPUTNAME..."%(self.name,))
		var = event[0]
		dev = self.storage[Name(*event[1:])]
		setattr(self.parent.ctx,var,dev.read())

@main_words.register_statement
class InputVar(IOvar):
	storage = Inputs
	name="var input"
	doc="assign a variable to get an input value"
	long_doc=u"""\
var input NAME ‹inputname›…
        : Read the named input and store it in the variable ‹NAME›.
          Note: The value will be fetched when this statement is executed,
          not when the value is used.
"""

@main_words.register_statement
class OutputVar(IOvar):
	storage = Outputs
	name="var output"
	doc="assign a variable to get an output's current value"
	long_doc=u"""\
var output NAME ‹outputname›…
        : Read the named output's current value and store it in the variable ‹NAME›.
          Whether the actual or the intended value is read depends on the hardware.
          Note: The value will be fetched when this statement is executed,
          not when the value is used.
"""


@main_words.register_statement
class IOset(AttributedStatement):
	timespec = None
	nextval = None
	force = True # for timing
	async = False
	name="set output"
	doc="set an output to some value"
	long_doc=u"""\
set output VALUE ‹outputname›…
        : The named output is set to ‹VALUE›.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError("Usage: set output VALUE OUTPUTNAME...")
		val = event[0]
		dev = Outputs[Name(*event[1:])]
		if self.timespec is None:
			timer = None
		else:
			timer = self.timespec()
		dev.write(val, timer=timer, nextval=self.nextval, async=self.async)

IOset.register_statement(DelayFor)
IOset.register_statement(DelayWhile)
IOset.register_statement(DelayUntil)
IOset.register_statement(DelayNext)
@IOset.register_statement
class IOasync(Statement):
	name = "async"
	doc = "don't wait for completion"
	long_doc=u"""\
async
	- don't wait for completion.
	  This only applies to resetting after delay specified with for/until/… sub-statements.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u'Usage: async')

		self.parent.async = True





class IOisSet(Check):
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if %s VALUE NAME…" % (self.name,))
		return self.storage[Name(*args[1:])].read() == args[0]

@register_condition
class InputIsSet(IOisSet):
	storage = Inputs.storage
	name="input"
	doc="Test if an input is set to a specific value"

@register_condition
class OutputIsSet(IOisSet):
	storage = Outputs.storage
	name="output"
	doc="Test if an output is set to a specific value"

