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

"""\
This code does basic state handling (both persistent and not).

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
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.run import process_event,process_failure
from homevent.event import Event
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name
from homevent.collect import Collection,Collected
from homevent.times import now,humandelta
from homevent.twist import fix_exception

import os,sys

Db = None

class States(Collection):
    name = "state"
States = States()
States.does("del")

class StateChangeError(Exception):
	no_backtrace = True
	def __init__(self,s,v):
		self.state = s
		self.value = v
	def __str__(self):
		s = self.state
		return "Trying to change state to '%s' while changing from '%s' to '%s'" % (self.value,s.old_value,s.value)

class State(Collected):
	storage = States.storage

	def __init__(self, *name):
		self.value = None
		self.working = False
		super(State,self).__init__(*name)
	
	def init(self):
		pass

	def delete(self,ctx):
		if self.working:
			raise StateChangeError(self,u"‹deleted›")
		self.working = True
		self.time = now()
		try:
			if self.value is not None:
				process_event(Event(ctx,"state",self.value,"-",*self.name))
		finally:
			self.delete_done()

	def set_value(self, val):
		self.value = val

	def list(self):
		yield super(State,self)
		yield ("value", self.value)
		yield ("lock", ("Yes" if self.working else "No"))
		if hasattr(self,"old_value"):
			yield ("last value",self.old_value)
			yield ("last change",humandelta(now()-self.time))

	def info(self):
		if hasattr(self,"old_value"):
			return u"%s — %s " % (self.value,humandelta(now()-self.time))
		else:
			return unicode(self.value)

class SavedState(State):
	def __init__(self, *name):
		super(SavedState,self).__init__(*name)
		del self.value
	
		global Db
		if Db is None:
			from homevent.database import DbStore
			Db = DbStore(category="state")
		try:
			self.value = Db.get(self.name)
		except KeyError:
			self.value = None

	def set_value(self,val):
		if val is None:
			Db.delete(self.name)
		else:
			Db.set(self.name,val)
		self.value = val

	def delete(self,ctx):
		Db.delete(self.name)
		super(SavedState,self).delete(ctx)

	def list(self):
		yield super(SavedState,self)
		yield ("persistent","yes")

	
class StateHandler(AttributedStatement):
	name=("state",)
	doc="Create a state variable"
	long_doc="""\
state name...
	: creates an empty named state
"""
	trigger = None
	ptrigger = None
	coll = State

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: state ‹name…›")
		s = self.coll(*event)
		s.working = True
		try:
			if hasattr(self,"value") and s.value is None:
				s.set_value(self.value)
			s.time = now()
			if s.value is None and self.trigger \
					or s.value is not None and self.ptrigger:
				old = s.old_value if s.old_value is not None else "-"
				val = s.value
				if val is None: val = "-"
				process_event(Event(self.ctx,"state",old,self.value,*s.name))
		except BaseException:
			s.delete_done()
			raise
		finally:
			s.working = False

class ValueHandler(Statement):
	name=("value",)
	doc="Set the initial value"
	long_doc="""\
value ‹whatever›
	: sets the initial value of the state, without sending an event
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u"Usage: value ‹whatever›")

		if hasattr(self.parent,"value"):
			raise SyntaxError(u"The 'value' substatement can only be used once")
		elif event[0] != "-":
			self.parent.value = event[0]
		else:
			self.parent.value = None
StateHandler.register_statement(ValueHandler)

class SavedHandler(Statement):
	name=("saved",)
	doc="Keep the state between runs"
	long_doc="""\
saved 
	: save/restore the state between invocations of HomEvenT
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u"Usage: saved")
		self.parent.coll = SavedState
StateHandler.register_statement(SavedHandler)

class TriggerHandler(Statement):
	name=("trigger",)
	doc="Signal when a state is created"
	long_doc="""\
trigger new
	: sends a standard value-changed signal upon state creation
trigger old
	: same, when a saved state is restored
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: trigger new")
		for v in event:
			if v == "new":
				self.parent.trigger = True
			elif v == "old":
				self.parent.ptrigger = True
			else:
				raise SyntaxError(u"Usage: trigger new")
StateHandler.register_statement(TriggerHandler)


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
		s = States[name]
		old = s.value
		if old is None:
			old = "-"
		if value == old:
			return # no change!

		if s.working:
			raise StateChangeError(s,value)
		s.working = True
		try:
			s.old_value = s.value
			s.set_value(value if value != "-" else None)
			s.time = now()
			try:
				process_event(Event(self.ctx,"state",old,value,*s.name))
			except Exception as e:
				fix_exception(e)
				process_failure(e)
		finally:
			s.working = False

class ForgetStateHandler(Statement):
	name=("forget","state")
	doc="delete a saved state from the persistent database"
	long_doc="""\
forget state name...
	- removes this saved state from the database
	  The value will be re-added the next time the state is changed!
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: forget state ‹name…›")
		name = Name(event)

		global Db
		if Db is None:
			from homevent.database import DbStore
			Db = DbStore(category="state")

		Db.delete(name)


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
		s = States[name]
		setattr(self.parent.ctx,var,s.value if not s.working else s.old_value)


class StateCheck(Check):
	name=("state",)
	doc="check if a state has a particular value"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if state ‹value› ‹name…›")
		value = args[0]
		name = Name(args[1:])
		return States[name].value == value


class StateLockedCheck(Check):
	name=("locked","state")
	doc="check if a state is being updated"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if state locked ‹name…›")
		return States[Name(args)].working


class LastStateCheck(Check):
	name=("last","state")
	doc="check if a state had a particular value before"
	def check(self,*args):
		if len(args) < 2:
			raise SyntaxError(u"Usage: if last state ‹value› ‹name…›")
		value = args[0]
		name = Name(args[1:])

		s = States[name]
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
		return name in States


class SavedStateCheck(Check):
	name=("saved","state")
	doc="check if a state is stored in the persistent database"

	def check(self,*args):
		if len(args) < 1:
			raise SyntaxError(u"Usage: if saved state ‹name…›")

		global Db
		if Db is None:
			from homevent.database import DbStore
			Db = DbStore(category="state")
		try:
			Db.get(Name(args))
		except KeyError:
			return False
		else:
			return True


class StateModule(Module):
	"""\
		This is a module to store system state.
		"""

	info = "store state"

	def load(self):
		main_words.register_statement(StateHandler)
		main_words.register_statement(SetStateHandler)
		main_words.register_statement(VarStateHandler)
		register_condition(StateCheck)
		register_condition(StateLockedCheck)
		register_condition(LastStateCheck)
		register_condition(ExistsStateCheck)
		register_condition(SavedStateCheck)
	
	def unload(self):
		main_words.unregister_statement(StateHandler)
		main_words.unregister_statement(SetStateHandler)
		main_words.unregister_statement(VarStateHandler)
		main_words.unregister_statement(ForgetStateHandler)
		unregister_condition(StateCheck)
		unregister_condition(StateLockedCheck)
		unregister_condition(LastStateCheck)
		unregister_condition(ExistsStateCheck)
		unregister_condition(SavedStateCheck)
	
init = StateModule
