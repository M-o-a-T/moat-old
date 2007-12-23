# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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
This code does basic persistent state handling.

set state X NAME
	sets the named state to X
	triggers an event if that changed
	raises an error if you're recursing
del state NAME
	forgets about that state
if state X NAME
	checks if the state is that
var state X NAME
	makes the state named NAME available as the variable X
list state [NAME]
	shows all states / only that one

"""

from homevent.module import Module
from homevent.statement import Statement, main_words,global_words
from homevent.logging import log, Logger, register_logger,unregister_logger
from homevent.run import process_event
from homevent.event import Event
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name

from time import time
import os

states = {}

class StateChangeError(Exception):
	def __init__(self,s,v):
		self.state = s
		self.value = v
	def __str__(self):
		s = self.state
		return "Trying to change state to '%s' while changing from '%s' to '%s'" % (self.value,s.old_value,s.value)

class State(object):
	def __init__(self, *name):
		if name in states:
			raise RuntimeError("duplicate state: "+" ".join(name))
		self.name = name
		self.value = None
		self.working = False
		states[self.name] = self

	def delete(self):
		del states[self.name]

class SetStateHandler(Statement):
	name=("set","state")
	doc="set some state to something"
	long_doc="""\
set state X name...
	: sets the named state to X
	: triggers an event if that changed
	: raises an error if that event tries to change the state again
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2:
			raise SyntaxError(u"Usage: set state ‹value› ‹name…›")
		value = event[0]
		name = Name(event[1:])
		try:
			s = states[name]
		except KeyError:
			s = State(*name)
			old = "-"
		else:
			old = s.value

		if value == old:
			return None # no change!
		if s.working:
			raise StateChangeError(s,value)
		s.working = True
		s.old_value = s.value
		s.value = value
		s.time = time()
		d = process_event(Event(self.ctx,"state",old,value,*name))
		def clear_chg(_):
			s.working = False
			return _
		d.addBoth(clear_chg)
		return d


class ListStateHandler(Statement):
	name=("list","state")
	doc="show current state"
	long_doc="""\
list state
	: shows all state variables
list state name...
	: shows the current (and previous) value of that state
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			s = states[Name(event)]
			print >>self.ctx.out, "Name:"," ".join(s.name)
			print >>self.ctx.out, "Value:",s.value
			if hasattr(s,"old_value"):
				print >>self.ctx.out, "Last Value:",s.old_value
				if "HOMEVENT_TEST" not in os.environ:
					print >>self.ctx.out, "Last Change:",s.time
		else:
			for s in states.itervalues():
				print >>self.ctx.out,"%s = %s" % (" ".join(s.name),s.value)
			print >>self.ctx.out, "."


class DelStateHandler(Statement):
	name=("del","state")
	doc="delete a state"
	long_doc="""\
del state name...
	: deletes all memory of that state
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: del state ‹name…›")

		s = states[Name(event)]
		if s.working:
			raise StateChangeError(s,u"‹deleted›")
		s.working = True
		s.time = time()
		d = process_event(Event(self.ctx,"state",s.value,"-",*event))
		def clear_chg(_):
			del states[Name(event)]
			return _
		d.addBoth(clear_chg)
		return d


class VarStateHandler(Statement):
	name=("var","state")
	doc="assign a variable to report a state"
	long_doc=u"""\
var state NAME name...
	: $NAME refers to the state ‹name…›, in the enclosing block
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(event[1:])
		s = states[name]
		setattr(self.parent.ctx,var,s.value if not s.working else s.old_value)


class StateCheck(Check):
	name=("state",)
	doc="check if a state has a particular value"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if state ‹value› ‹name…›")
		value = args[0]
		name = Name(args[1:])
		return states[name].value == value


class StateLockedCheck(Check):
	name=("locked","state")
	doc="check if a state is being updated"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if state locked ‹name…›")
		return states[Name(args)].working


class LastStateCheck(Check):
	name=("last","state")
	doc="check if a state had a particular value before"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if last state ‹value› ‹name…›")
		value = args[0]
		name = Name(args[1:])

		s = states[name]
		if hasattr(s,"old_value"):
			return s.old_value == value
		else:
			return value == "-"


class ExistsStateCheck(Check):
	name=("exists","state")
	doc="check if a state exists at all"
	def check(self,*args):
		if len(args) < 1:
			raise SyntaxError(u"Usage: if exists state ‹name…›")
		name = Name(args)
		return name in states


class StateModule(Module):
	"""\
		This is a module to store system state.

		Persistency is planned.
		"""

	info = "store NONpersistent state"

	def load(self):
		main_words.register_statement(SetStateHandler)
		main_words.register_statement(VarStateHandler)
		global_words.register_statement(ListStateHandler)
		main_words.register_statement(DelStateHandler)
		register_condition(StateCheck)
		register_condition(StateLockedCheck)
		register_condition(LastStateCheck)
		register_condition(ExistsStateCheck)
	
	def unload(self):
		main_words.unregister_statement(SetStateHandler)
		main_words.unregister_statement(VarStateHandler)
		global_words.unregister_statement(ListStateHandler)
		main_words.unregister_statement(DelStateHandler)
		unregister_condition(StateCheck)
		unregister_condition(StateLockedCheck)
		unregister_condition(LastStateCheck)
		unregister_condition(ExistsStateCheck)
	
init = StateModule
