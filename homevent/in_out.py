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

from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.context import Context
from homevent.event import Event
from homevent.base import Name,SName
from homevent.run import process_failure
from homevent.collect import Collection,Collected
from homevent.twist import fix_exception,reraise,Jobber

import os
import sys
import socket
import errno

class Inputs(Collection):
	name = "input"
Inputs = Inputs()
Inputs.does("del")

class Outputs(Collection):
	name = "output"
Outputs = Outputs()
Outputs.does("del")

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
			delta = now() - self.last_time
			delta = unixdelta(delta)
			yield ("last read", humandelta(delta))
			yield ("last value",self.last_value)

	def _read(self):
		"""Read an input. Override this."""
		raise NotImplementedError("You need to override %s._read()" % (self.__class__.__name__,))

	def read(self):
		"""Read an input, check range."""
		res = self._read()
		res = self.repr(res)
		self.check(res)
		self.last_time = now()
		return self.last_value

	def repr(self, res):
		"""Represent the input, i.e. translate input values to script data"""
		return res

	def repr_range(self, res):
		"""Represent the input when it's from a continuous range"""
		return self.repr(res)

	def repr_value(self, res):
		"""Represent the input when it's from a distinct set"""
		return self.repr(res)


class Output(CommonIO):
	"""This represents a single output."""
	storage = Outputs
	last_value = None

	typ = "???output"

	def list(self):
		for r in super(Output,self).list():
			yield r
		if self.last_value is not None:
			delta = now() - self.last_time
			delta = unixdelta(delta)
			yield ("last write", humandelta(delta))
			yield ("last value",self.last_value)

	def _write(self,val):
		"""Write an output. Override this."""
		raise NotImplementedError("You need to override %s._write()" % (self.__class__.__name__,))

	def write(self,val):
		"""Read an input, check range."""
		wval = self.trans(val)
		check(val)
		self._write(wval)

		self.last_value = wval
		self.last_time = now()

	def trans(self, val):
		"""Translate the output, i.e. script data to input values"""
		return val

class BoolIO(object):
	"""A boolean mix-in. Add *before* Input or Output class."""
	def __init__(self,name):
		super(BoolIO,self).__init__(name, values=(False,True,"on","off","False","True",0,1,"0","1"))

	def trans(self,res):
		if str(val).lower() in ("on","true","1"):
			return True
		if str(val).lower() in ("off","false","0"):
			return False
		raise BadValue(self.name, val)

	def repr_value(self,res):
		if res:
			return "on"
		else:
			return "off"
	

class MakeIO(AttributedStatement):
	"""Common base class for input and output creation statements"""
	ranges = None
	values = None
	addons = None

	dest = None

	def __init__(self,*a,**k):
		super(MakeIO,self).__init__(*a,**k)
		self.ranges = []
		self.values = []
		self.addons = {}

	def run(self,ctx,**k):
		event = self.params(ctx)
		if self.dest is None:
			self.dest = Name(event[0])
			typ = event[1]
			d = 2
		else:
			typ = event[0]
			d = 1

		self.registry[typ](self.dest.apply(ctx), event.apply(ctx,drop=d), self.addons,self.ranges,self.values)


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



@MakeInput.register_statement
@MakeOutput.register_statement
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

@MakeInput.register_statement
@MakeOutput.register_statement
class IORange(Statement):
	name="range"
	dest = None
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

@MakeInput.register_statement
@MakeOutput.register_statement
class IOValue(Statement):
	name="value"
	dest = None
	doc="specify single allowed values"

	long_doc = u"""\
value ‹val›…
  - Tell this input that it accepts this particular value.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			 raise SyntaxError(u'Usage: value ‹val›…')
		self.parent.ranges.extend(event)


@main_words.register_statement
class IOvar(Statement):
        name="var input"
        doc="assign a variable to get an input value"
        long_doc=u"""\
var input NAME ‹inputname›…
        : Read the named input and store it in the variable ‹NAME›.
          Note: The value will be fetched when this statement is executed,
          not when the value is used.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError("Usage: var input NAME INPUTNAME...")
		var = event[0]
		dev = Inputs[Name(*event[1:])]
		setattr(self.parent.ctx,var,dev.read())


@main_words.register_statement
class IOset(Statement):
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
		dev.write(val)


class IOExists(Check):
	def check(self,*args):
		return Name(*args) in self.storage

@register_condition
class InputExists(IOExists):
	storage = Inputs.storage
	name="exists input"
	doc="Test if a named input exists"

@register_condition
class OutputExists(IOExists):
	storage = Outputs.storage
	name="exists output"
	doc="Test if a named output exists"

