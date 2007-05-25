#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does basic configurable event mangling.

on switch *state livingroom *switch:
	send change $state lights livingroom $switch

on switch * * *:
	if neq $2 outside
	if state on alarm internal
	trigger alarm $2

Given the event "switch on livingroom main", this would cause a
"change on lights livingroom main" event if the internal alarm is off.
Otherwise a "alarm livingroom" would be triggered.

"""

from homevent.parser import SimpleStatement,ComplexStatement,\
	ImmediateCollectProcessor, main_words
from homevent.logging import log_event,log, TRACE

__all__ = ["register_actor","unregister_actor"]

onHandlers = {}
_onHandler_id = 0

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

class OnEventHandler(ComplexStatement):
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
	in_sub = False

	def get_processor(self):
		return ImmediateCollectProcessor(parent=self, ctx=self.ctx(words=self))
	processor = property(get_processor)

	def __repr__(self):
		try:
			return "‹"+self.__class__.__name__+"("+str(self.handler_id)+")›"
		except AttributeError:
			try:
				return "‹"+self.__class__.__name__+repr(self.args)+"›"
			except AttributeError:
				return "‹"+self.__class__.__name__+"(?)›"

	def input(self,event,**k):
		raise SyntaxError("‹on ...› can only be used as a complex statement")

	def input_complex(self,w):
		w = w[len(self.name):]
		log(TRACE, "Create OnEvtHandler: "+repr(w))
		self.args = w

	def add(self,*a,**k):
		log(TRACE, "add",a,k)

	def done(self):
		global _onHandler_id
		_onHandler_id += 1
		self.handler_id = _onHandler_id
		log(TRACE,"NewHandler",self.handler_id)
		onHandlers[self.handler_id] = self

class OffEventHandler(SimpleStatement):
	name = ("drop","on")
	doc = "forget about this event handler"
	def input(self,event,**k):
		w = event[len(self.name):]
		if len(w) == 1:
			del onHandlers[w[0]]
		else:
			raise SyntaxError("Usage: drop on ‹handler_id›")

class OnListHandler(SimpleStatement):
	name = ("list","on")
	doc = "list event handlers"
	def input(self,event,**k):
		w = event[len(self.name):]
		if not len(w):
			try:
				fl = len(str(max(onHandlers.iterkeys())))
			except ValueError:
				print >>self.ctx.out,"No handlers are defined."
			else:
				for id in sorted(onHandlers.iterkeys()):
					h = onHandlers[id]
					print >>self.ctx.out,str(id)+" "*(fl-len(str(id))+1),": ", \
						" ".join(h.args)
		elif len(w) == 1:
			h = onHandlers[w[0]]
			print >>self.ctx.out, h.handler_id,":"," ".join(h.name)
			if hasattr(h,"realname"): print >>self.ctx.out,"Name:",h.realname
			if hasattr(h,"doc"): print >>self.ctx.out,"Doc:",h.doc
		else:
			raise SyntaxError("Usage: list on ‹handler_id›")


class DoNothingHandler(SimpleStatement):
	name = ("do","nothing")
	doc = "do not do anything"
	long_doc="""\
This statement does not do anything. It's a placeholder if you want to
explicitly state that some event does not result in any action.
"""
	def input(self,event,**k):
		w = event[len(self.name):]
		if len(w):
			raise SyntaxError("Usage: do nothing")
		log(TRACE,"NOW: do nothing")


def load():
	main_words.register_statement(OnEventHandler)
	main_words.register_statement(OffEventHandler)
	main_words.register_statement(OnListHandler)
	OnEventHandler.register_statement(DoNothingHandler)

def unload():
	main_words.unregister_statement(OnEventHandler)
	main_words.unregister_statement(OffEventHandler)
	main_words.unregister_statement(OnListHandler)
	OnEventHandler.unregister_statement(DoNothingHandler)

