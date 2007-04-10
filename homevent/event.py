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
	def __init__(self, *name):
		"""\
			Events have at least one name. For example:
				Event("startup")
				Event("sw12","toggle")
				Event("lamp12","dim","10")
			"""
		if not len(name):
			raise EventNoNameError
		self.names = name

		global event_id
		event_id += 1
		self.id = event_id

	def __repr__(self):
		if not hasattr(self,"names"):
			return "Event(<uninitialized>)"
		return "Event(%s)" % ",".join(repr(n) for n in self.names)

	def __str__(self):
		return "↯."+".".join(self.names)

	def report(self, verbose=False):
		yield "EVENT: "+".".join(self.names)
	
	def __getitem__(self,i):
		"""… so that you can write e[0] instead of e.names[0]"""
		return self.names[i]
	
	def __setitem__(self,i,j):
		raise RuntimeError("You cannot modify an event!")

class ExceptionEvent(Event, failure.Failure):
	"""\
		This event tracks that something went wrong.
		"""
	def __init__(self, e1=None,e2=None,e3=None, within=()):
		failure.Failure.__init__(self, e1,e2,e3)
		try:
			Event.__init__(self,"exception",self.type.__name__)
		except AttributeError: # old-style class!
			Event.__init__(self,"exception",str(self.type))

		self.within=within
		if within:
			self.id = self.within[0].id
	
	def report(self, verbose=False):
		if verbose:
			from traceback import format_exception
			exc = format_exception(self.type,self.value,self.tb)
			p = "ERROR: "
			for r in exc:
				for l in r.rstrip("\n").split("\n"):
					yield p+l
					p="     : "
		else:
			yield "ERROR: "+failure.Failure.__str__(self)
		for w in self.within:
			p = "   in: "
			for r in w.report(verbose):
				yield p+r
				p = "     : "

