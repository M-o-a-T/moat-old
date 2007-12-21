# -*- coding: utf-8 -*-
"""\
	This module holds a few random constants and stuff.
	"""
SYS_PRIO = -10
MIN_PRIO = 0
MAX_PRIO = 100

class Name(tuple):
	"""A class that knows how to print itself the "right" way"""
	delim = u"¦"
	prefix = ""
	suffix = ""

	def __str__(self):
		return unicode(self).encode("utf-8")
	def __unicode__(self):
		return self.prefix + self.delim.join((unicode(x) for x in self)) + self.suffix
	def __repr__(self):
		return self.__class__.__name__+super(Name,self).__repr__()
