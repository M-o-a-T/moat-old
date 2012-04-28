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

from homevent.interpreter import CollectProcessor
from homevent.statement import Statement,MainStatementList, main_words,\
	global_words
from homevent.logging import log_event,log, TRACE
from homevent.run import register_worker,unregister_worker,MIN_PRIO,MAX_PRIO
from homevent.worker import HaltSequence,Worker
from homevent.module import Module
from homevent.logging import log
from homevent.check import Check,register_condition,unregister_condition
from homevent.event import TrySomethingElse
from homevent.base import Name,SName
from homevent.collect import Collection,Collected

from twisted.internet import defer

onHandlers = {}
onHandlers2 = {}

class _OnHandlers(Collection):
	name = "on"

	def iteritems(self):
		def priosort(a,b):
			a=self[a]
			b=self[b]
			return cmp(a.prio,b.prio) or cmp(a.name,b.name)
		for i in sorted(self.iterkeys(), cmp=priosort):
			yield i,self[i]

	def __getitem__(self,key):
		try:
			return super(_OnHandlers,self).__getitem__(key)
		except KeyError:
			if key in onHandlers:
				return onHandlers[key]
			if key in onHandlers2:
				return onHandlers2[key][0]
			if hasattr(key,"__len__") and len(key) == 1:
				if key[0] in onHandlers:
					return onHandlers[key[0]]
				if key[0] in onHandlers2:
					return onHandlers2[key[0]][0]
			raise

	def __setitem__(self,key,val):
		assert val.name==key, repr(val.name)+" != "+repr(key)
		onHandlers[val.id] = val
		try:
			onHandlers2[val.parent.arglist].append(val)
		except KeyError:
			onHandlers2[val.parent.arglist] = [val]
		super(_OnHandlers,self).__setitem__(key,val)
		register_worker(val)

	def __delitem__(self,key):
		val = self[key]
		unregister_worker(val)
		del onHandlers[val.id]
		onHandlers2[val.parent.arglist].remove(val)
		if not onHandlers2[val.parent.arglist]:
			del onHandlers2[val.parent.arglist]
		super(_OnHandlers,self).__delitem__(val.name)

	def pop(self,key):
		val = self[key] if key else self.keys()[0]
		unregister_worker(val)
		del OnHandlers[val.id]
		try:
			del OnHandlers2[val.parent.arglist]
		except KeyError:
			pass
		return val
OnHandlers = _OnHandlers()
OnHandlers.does("del")

class BadArgs(RuntimeError):
	def __str__(self):
		return "Mismatch: %s does not fit %s" % (repr(self.args[0]),repr(self.args[1]))

class BadArgCount(RuntimeError):
	def __str__(self):
		return "The number of event arguments does not match"


class iWorker(Worker):
	"""This is a helper class, to pass the event name to Worker.__init__()"""
	def __init__(self):
		super(iWorker,self).__init__(self.name)

class OnEventWorker(Collected,iWorker):
	storage = OnHandlers.storage
	def __init__(self,parent, name=None, prio=(MIN_PRIO+MAX_PRIO)//2+1):
		self.prio = prio
		self.parent = parent

		if name is None:
			name = Name("_on",self._get_id())
		super(OnEventWorker,self).__init__(*name)

#		self.name = unicode(self.parent.arglist)
#		if self.parent.displayname is not None:
#			self.name += u" ‹"+" ".join(unicode(x) for x in self.parent.displayname)+u"›"

		
		log(TRACE,"NewHandler",self.id)

	def does_event(self,event):
		ie = iter(event)
		ia = iter(self.parent.arglist)
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
			if hasattr(a,"startswith") and a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else:
					a = a[1:]
				ctx[a] = e
			elif str(a) != str(e):
				return False

	def process(self, **k):
		super(OnEventWorker,self).process(**k)
		return self.parent.process(**k)

	def report(self, verbose=False):
		if not verbose:
			for r in super(OnEventWorker,self).report(verbose):
				yield r
		else:
			for r in self.parent.report(verbose):
				yield r

	def delete(self,ctx=None):
		self.delete_done()

	def info(self):
		return u"%s (%d)" % (unicode(self.parent.arglist),self.prio)

	def list(self):
		for r in super(OnEventWorker,self).list():
			yield r
		yield("id",self.id)
		yield("prio",self.prio)
		if self.parent.displayname is not None:
			yield("pname"," ".join(unicode(x) for x in self.parent.displayname))
		yield("args",self.parent.arglist)
		yield("prio",self.prio)
		if hasattr(self.parent,"displaydoc"):
			yield("doc",self.parent.displaydoc)



class OnEventHandler(MainStatementList):
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
	displayname = None

	def grab_args(self,event,ctx):
		### This is a pseudo-clone of grab_event()
		ie = iter(event)
		ia = iter(self.arglist)
		pos = 0
		while True:
			try: e = ie.next()
			except StopIteration: e = StopIteration
			try: a = ia.next()
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return
			if e is StopIteration or a is StopIteration:
				raise BadArgCount
			if hasattr(a,"startswith") and a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else:
					a = a[1:]
				setattr(ctx,a,e)
			elif str(a) != str(e):
				raise BadArgs(a,e)
		
	def process(self, event=None,**k):
		if event:
			ctx = self.ctx(ctx=event.ctx)
			self.grab_args(event,ctx)
		else:
			ctx = self.ctx()
		return super(OnEventHandler,self).run(ctx)

	def run(self,ctx,**k):
		if self.procs is None:
			raise SyntaxError(u"‹on ...› can only be used as a complex statement")

		worker = OnEventWorker(self,name=self.displayname,prio=self.prio)

	def start_block(self):
		super(OnEventHandler,self).start_block()
		w = Name(*self.params(self.ctx))
		log(TRACE, "Create OnEvtHandler:", w)
		self.arglist = w

	def _report(self, verbose=False):
		if self.displayname is not None:
			if isinstance(self.displayname,basestring):
				yield "name: "+self.displayname
			else:
				yield "name: "+" ".join(unicode(x) for x in self.displayname)
		yield "prio: "+str(self.prio)

		for r in super(OnEventHandler,self)._report(verbose):
			yield r


class OnPrio(Statement):
	name = ("prio",)
	doc = "prioritize event handler"
	immediate = True
	long_doc="""\
This statement prioritizes an event handler.
If two handlers have the same priority and both match,
the order they (attempt to) run in is undefined.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u"Usage: prio ‹priority›")
		try:
			prio = int(event[0])
		except (ValueError,TypeError):
			raise SyntaxError(u"Usage: prio ‹priority› ⇐ integer priorities only")
		if prio < MIN_PRIO or prio > MAX_PRIO:
			raise ValueError("Priority value (%d): needs to be between %d and %d" % (prio,MIN_PRIO,MAX_PRIO))
		self.parent.prio = prio


class OnName(Statement):
	name = ("name",)
	doc = "name an event handler"
	immediate = True
	long_doc="""\
This statement assigns a name to an event handler.
(Useful when you want to delete it...)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: name "‹text›"')
		self.parent.displayname = SName(event)


class OnDoc(Statement):
	name = ("doc",)
	doc = "document an event handler"
	immediate = True
	long_doc="""\
This statement assigns a documentation string to an event handler.
(Useful when you want to document what the thing does ...)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: doc "‹text›"')
		self.parent.displaydoc = event[0]


class OnSkip(Statement):
	name = ("next","handler")
	doc = u"skip ahead to the next on… event handler"
	long_doc="""\
This statement causes processing to skip ahead to the next-higher-priority
event handler.
Commands in the same handler, after this one, are *not* executed.
"""
	def run(self,ctx,**k):
		raise TrySomethingElse()


class OnExistsCheck(Check):
	name=("exists","on")
	doc="check if a handler exists"
	long_doc="""\
if exists on FOO BAR: check if a handler for this event exists
"""
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists on ‹name…›")
		name = Name(*args)
		return name in OnHandlers


class OnEventModule(Module):
	"""\
		This module registers the "on EVENT:" handler.
		"""

	info = "the 'on EVENT:' handler"

	def load(self):
		main_words.register_statement(OnEventHandler)
		OnEventHandler.register_statement(OnPrio)
		main_words.register_statement(OnSkip)
		OnEventHandler.register_statement(OnName)
		OnEventHandler.register_statement(OnDoc)
		register_condition(OnExistsCheck)
	
	def unload(self):
		main_words.unregister_statement(OnEventHandler)
		OnEventHandler.unregister_statement(OnPrio)
		main_words.unregister_statement(OnSkip)
		OnEventHandler.unregister_statement(OnName)
		OnEventHandler.unregister_statement(OnDoc)
		unregister_condition(OnExistsCheck)
	
init = OnEventModule

