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
	def __init__(self, *names):
		"""\
			Events have at least one name. For example:
				Event("startup")
				Event("sw12","toggle")
				Event("lamp12","dim","10")
			"""
		if not len(names):
			raise EventNoNameError
		self.names = names

		global event_id
		event_id += 1
		self.id = event_id


	def __repr__(self):
		if not hasattr(self,"names"):
			return "Event(<uninitialized>)"
		return "Event(%s)" % ",".join(repr(n) for n in self.names)

	def __str__(self):
		try:
			return "↯."+"¦".join(self.names)
		except Exception:
			return "↯ REPORT_ERROR: "+repr(self.names)

	def report(self, verbose=False):
		try:
			yield "EVENT: "+"¦".join(self.names)
		except Exception:
			yield "EVENT: REPORT_ERROR: "+repr(self.names)
	
	def __getitem__(self,i):
		"""… so that you can write e[0] instead of e.names[0]"""
		return self.names[i]
	
	def __getslice__(self,i,j):
		"""… so that you can write e[2:] instead of e.names[2:]"""
		return self.names[i:j]
	
	def __setitem__(self,i,j):
		raise RuntimeError("You cannot modify an event!")

	def __len__(self):
		return len(self.names)
	def __bool__(self):
		return True

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
			yield "   at: "+cmd.file+":"+str(cmd.line)
		if hasattr(self,"within"):
			for w in self.within:
				p = "   in: "
				for r in w.report(verbose):
					yield p+r
					p = "     : "
	else:
		yield "ERROR: "+self.getErrorMessage()
Failure.report = report
