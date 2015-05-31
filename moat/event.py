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

"""\
This part of the code defines what an event is.
"""

from __future__ import division,absolute_import

import warnings
from moat.base import Name,RaisedError
from moat.context import Context

class TrySomethingElse(RuntimeError):
	"""Error if a conditional does not match"""
	def __init__(self,*args):
		self.args = args
	def __str__(self):
		return "Cannot proceed (%s)" % " ".join((str(x) for x in self.args))

class StopParsing(BaseException):
	"""Quit the current parser."""
	pass

class NeverHappens(BaseException):
	"""This exception is never raised. Needed for conditional handling."""
	pass

class EventNoNameError(ValueError):
	"""\
		You tried to create an unnamed event. That's stupid.
		"""
	pass

event_id = 0

class Event(object):
	"""\
		This is an event. It happens and gets analyzed by the system.
		"""
	loglevel = None
	def __init__(self, ctx, *name):
		"""\
			Events have a context and at least one name. For example:
				Event(ctx, "startup")
				Event(ctx, "switch","toggle","sw12")
				Event(ctx, "switch","dim","livingroom","lamp12")
				Event(ctx, "timer","timeout","t123")
			"""
		self._name_check(name)
		#print "E_INIT",name,"with",ctx
		self.name = Name(name)
		self.ctx = ctx if ctx is not None else Context()
		if "loglevel" in self.ctx:
			self.loglevel = ctx.loglevel

		global event_id
		event_id += 1
		self.id = event_id

	def _name_check(self,name):
		if not len(name):
			raise EventNoNameError

	def __repr__(self):
		if not hasattr(self,"name"):
			return "%s(<uninitialized>)" % (self.__class__.__name__,)
		return "%s(%s)" % (self.__class__.__name__, ",".join(repr(n) for n in self.name))

	def __str__(self):
		try:
			return u"‹Event:%s›" % (self.name,)
		except Exception:
			return "<Event> REPORT_ERROR: "+repr(self.name)

	def __unicode__(self):
		try:
			return u"↯."+unicode(self.name)
		except Exception:
			return "↯ REPORT_ERROR: "+repr(self.name)

	def report(self, verbose=False):
		try:
			yield u"EVENT: "+unicode(self.name)
			for k,v in self.ctx:
				yield u"     : "+k+u"="+unicode(v)
		except Exception:
			yield "EVENT: REPORT_ERROR: "+repr(self.name)
	
	def list(self):
		yield (unicode(self.name),)
		if self.__class__ is not Event:
			yield ("type",self.__class__.__name__)
		if self.loglevel is not None:
			yield ("log level",self.loglevel)
		yield ("ctx",self.ctx)
	
	def __getitem__(self,i):
		u"""… so that you can write e[0] instead of e.name[0]"""
		return self.name[i]
	
	def __getslice__(self,i,j):
		u"""… so that you can write e[2:] instead of e.name[2:]"""
		return list(self.name[i:j])
		# list() because the result may need to be modified by the caller
	
	def __setitem__(self,i,j):
		raise RuntimeError("You cannot modify an event!")

	def __len__(self):
		return len(self.name)
	def __bool__(self):
		return True
	def __iter__(self):
		return self.name.__iter__()

	def apply(self, ctx=None, drop=0):
		"""\
			Copy an event, applying substitutions.
			This code dies with an AttributeError if there are no
			matching substitutes. This is intentional.
			"""
		w = []

		if ctx is None:
			ctx = self.ctx
		else:
			ctx = ctx(ctx=self.ctx)

		for n in self.name[drop:]:
			if hasattr(n,"startswith") and n.startswith('$'):
				r = ctx[n[1:]]
#				if n == "$X":
#					import sys
#					print >>sys.stderr,"c@%x %s %s"%(id(ctx),n,r)
#					for x in ctx._report():
#						print >>sys.stderr,": ",x
				n = r
			w.append(n)
		return self.__class__(ctx, *self.name.apply(ctx=ctx,drop=drop))

	def dup(self, ctx=None, drop=0):
		"""\
			Copy an event, NOT applying substitutions.
			"""
		w = []

		if ctx is None:
			ctx = self.ctx
		else:
			ctx = ctx(ctx=self.ctx)

		return self.__class__(ctx, *self.name[drop:])

