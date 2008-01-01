# -*- coding: utf-8 -*-

"""Class to make storing collections of stuff simpler"""

from weakref import WeakValueDictionary

collections = WeakValueDictionary()

class Collected(object):
	"""\
		This abstract class implements an object in a named subsystem
		which has a name and can be "list"ed and "del"eted.

		self.name can be set explicitly, before calling super().__init__(),
		if passing the name would be inconvenient due to multiple inheritance.
		"""
	_storage = None # class attribute

	def __init__(self, *name):
		if name:
			self.name = name
		elif not self.name:
			raise RuntimeError("Unnamed object of '%s'" % (self.__class__.__name__,))
			
		if self._storage is None:
			raise RuntimeError("You didn't declare a storage for '%s'" % (self.__class__.__name__,))
		self._storage[name] = self

	def list(self):
		"""Yield a couple of (left,right) tuples, for enumeration."""
		raise NotImplementedError("You need to override 'list' in '%s'" % (self.__class__.__name__,))

	def delete(self):
		"""Remove myself from a collection"""
		raise NotImplementedError("You need to override 'del' in '%s'" % (self.__class__.__name__,))

	def info(self):
		"""\
			Return a one-line string with additional data (but not the name!),
			if that makes sense.
			"""
		return None

class Collection(dict):
	"""\
		This class implements named collections of things.
		"""
	def __init__(cls,*name):

		if name in collections:
			raise RuntimeError(u"The collection ‹%s› already exists" % (self.name,))

		super(Collector,self).__init__()
		cls.storage = self
		collections[name] = cls

	
