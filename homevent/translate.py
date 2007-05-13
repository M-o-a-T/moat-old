#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does basic configurable event mangling.

on switch *state livingroom *switch:
	send change $state lights livingroom $switch

on switch * * *:
	if neq $2 outside
	if state on alarm internal
	send alarm $2

Given the event "switch on livingroom main", this would cause a
"change on lights livingroom main" event if the internal alarm is off.
Otherwise a "alarm livingroom" would be triggered.

"""

from homevent.parser import StatementBlock

__all__ = ["register_actor","unregister_actor"]

handlers = {}

def register_actor(handler):
	"""\
		Register a handler for a statement in an "on..." block.
		
		See homevent.parser.Statement and StatementBlock for details.
		"""
	if handler.name in handlers:
		raise ValueError("A handler for '%s' is already registered." % (handler.
name,))
	handlers[handler.name] = handler

def unregister_actor(handler):
	"""\
		Remove this actor.
		"""
	del handlers[handler.name]

class OnEventHandler(hp.StatementBlock):
	name=("on",)
	doc="on [event...]: [statements]"
	long_doc="""\
The OnEvent handler executes a statement (or a statement sequence)
when an event occurs.

Syntax:
	on [event...]:
		statement
		...

Every "*foo" in the event description is mapped to the corresponding
"$foo" argument in the list.
"""
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		self.name = w
		self.in_sub = False
	def input(self,*w):
		if not self.in_sub:
			raise InputError("‹on ...› can only be used as a compound statement")

	def input_obj(self,*w):
		log("Create SubBar: "+repr(w))
		self.in_sub = True
		return self
	def input_end(self):
		self.in_sub = False

def load():
	register_statement(EventHandler)

def unload():
	unregister_statement(EventHandler)

