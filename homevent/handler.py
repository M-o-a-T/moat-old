# -*- coding: utf-8 -*-

from __future__ import division

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
from homevent.run import register_worker,unregister_worker,MIN_PRIO,MAX_PRIO

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
	"""This is also a worker."""
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
	prio = (MIN_PRIO+MAX_PRIO)//2+1
	procs = None

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

	def does_event(self,event):
		ie = iter(event)
		ia = iter(self.args)
		ctx = {}
		pos = 0
		while True:
			try: e = ie.next()
			except StopIteration: e = StopIteration
			try: a = ia.next()
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return True
			if e is StopIteration or a is StopIteration:
				return False
			if a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else:
					a = a[1:]
				ctx[a] = e
			elif a != e:
				return False

	def run(self,event,**k):
		if self.procs is None:
			raise SyntaxError("‹on ...› can only be used as a complex statement")
		for a in self.procs:
			print "RUN ME ::", a

	def input_complex(self,w):
		w = w[len(self.name):]
		log(TRACE, "Create OnEvtHandler: "+repr(w))
		self.args = w
		self.procs = []

	def add(self,*a):
		log(TRACE, "add",a)
		self.procs.append(a)

	def done(self):
		global _onHandler_id
		_onHandler_id += 1
		self.handler_id = _onHandler_id
		log(TRACE,"NewHandler",self.handler_id)
		self.name = "¦".join(self.args)
		register_worker(self)
		onHandlers[self.handler_id] = self
	
	def report(self, verbose=False):
		yield "ON "+"¦".join(self.args)
		if not verbose: return
		yield "   prio: "+str(self.prio)
		pref="proc"
		for p in self.procs:
			yield "   "+pref+": "+str(p)
			pref="    "
	

class OffEventHandler(SimpleStatement):
	name = ("drop","on")
	doc = "forget about this event handler"
	def run(self,event,**k):
		w = event[len(self.name):]
		if len(w) == 1:
			worker = onHandlers[w[0]]
			unregister_worker(worker)
			del onHandlers[w[0]]
		else:
			raise SyntaxError("Usage: drop on ‹handler_id›")

class OnListHandler(SimpleStatement):
	name = ("list","on")
	doc = "list event handlers"
	def run(self,event,**k):
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
	def run(self,event,**k):
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

