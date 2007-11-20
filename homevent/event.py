# *-* coding: utf-8 *-*

"""\
This part of the code defines what an event is.
"""

import warnings
from twisted.python import failure

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
	def __init__(self, ctx, *names):
		"""\
			Events have a context and at least one name. For example:
				Event(ctx, "startup")
				Event(ctx, "switch","toggle","sw12")
				Event(ctx, "switch","dim","livingroom","lamp12")
				Event(ctx, "timer","timeout","t123")
			"""
		self._name_check(names)
		#print "E_INIT",names,"with",ctx
		self.names = names
		self.ctx = ctx

		global event_id
		event_id += 1
		self.id = event_id

	def _name_check(self,names):
		if not len(names):
			raise EventNoNameError

	def __repr__(self):
		if not hasattr(self,"names"):
			return "%s(<uninitialized>)" % (self.__class__.__name__,)
		return "%s(%s)" % (self.__class__.__name__, ",".join(repr(n) for n in self.names))

	def __str__(self):
		try:
			return "<Event:"+u"¦".join(unicode(x) for x in self.names)+">"
		except Exception:
			return "<Event> REPORT_ERROR: "+repr(self.names)

	def __unicode__(self):
		try:
			return u"↯."+u"¦".join(unicode(x) for x in self.names)
		except Exception:
			return "↯ REPORT_ERROR: "+repr(self.names)

	def report(self, verbose=False):
		try:
			yield u"EVENT: "+u"¦".join(unicode(x) for x in self.names)
		except Exception:
			yield "EVENT: REPORT_ERROR: "+repr(self.names)
	
	def __getitem__(self,i):
		u"""… so that you can write e[0] instead of e.names[0]"""
		return self.names[i]
	
	def __getslice__(self,i,j):
		u"""… so that you can write e[2:] instead of e.names[2:]"""
		return list(self.names[i:j])
		# list() because the result may need to be modified by the caller
	
	def __setitem__(self,i,j):
		raise RuntimeError("You cannot modify an event!")

	def __len__(self):
		return len(self.names)
	def __bool__(self):
		return True
	def __iter__(self):
		return self.names.__iter__()

	def clone(self, ctx=None, drop=0):
		"""\
			Copy an event, applying substitutions.
			This code dies with an AttributeError if there are no
			matching substitutes. This is intentional.
			"""
		w = []

		if ctx is None:
			ctx = self.ctx
		else:
			ctx = self.ctx(ctx=ctx)

		for n in self.names[drop:]:
			if hasattr(n,"startswith") and n.startswith('$'):
				n = getattr(ctx,n[1:])
			w.append(n)
		return self.__class__(ctx, *w)

#Monkey-patch t.p.f.Failure to answer to our report() call
from twisted.python.failure import Failure

def report(self, verbose=False):
	if verbose:
		from traceback import format_exception
		p = "ERROR: "
		for l in self.getTraceback().rstrip("\n").split("\n"):
			yield p+l
			p="     : "
		if hasattr(self,"cmd"):
			yield "   at: "+cmd.file+":"+unicode(cmd.line)
		if hasattr(self,"within"):
			for w in self.within:
				p = "   in: "
				for r in w.report(verbose):
					yield p+r
					p = "     : "
	else:
		yield "ERROR: "+self.getErrorMessage()
Failure.report = report
