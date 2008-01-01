# -*- coding: utf-8 -*-

"""Class to make storing collections of stuff simpler"""

from weakref import WeakValueDictionary,proxy

collections = WeakValueDictionary()


def CollectionNamer(name, bases, dico):
	"""\
		Add the collection to the dictionary, as long as it exists.
		(Specifically, a module unload is expected to remove it.)
		"""
	if bases == (dict,):
		return type(name, bases, dico) # abstract base class

	name = dico["name"]
	if isinstance(name,basestring):
		name = name.split()
	name = Name(dico["name"])
	if name in dico:
		return RuntimeError(u"A collection ‹%s› already exists" %(name,))

	dico["name"] = name
	cls = type(name, bases, dico)
	collections[name] = cls
	return cls


class Collection(dict):
	"""\
		This class implements named collections of things.

		Usage:
		
			class FooThings(Collection):
				name = "foo bar"

			class Foo(Collected):
				storage = FooThings

		A subsequent "list foo bar" command enumerates all known Foo objects.

		"""
	__metaclass__ = CollectionNamer

	# The Collected's storage needs to be a weak reference so that it
	# will be freed when the module is unloaded.
	@property
	def storage(self):
		return proxy(self)

	
class Collected(object):
	"""\
		This abstract class implements an object in a named subsystem
		which has a name and can be "list"ed and "del"eted.

		self.name can be set explicitly, before calling super().__init__(),
		if passing the name would be inconvenient due to multiple inheritance.

		You need to assign foo.storage to the "storage" class attribute,
		where foo is the associated Collection object.
		"""
	storage = None # Collection

	def __init__(self, *name):
		if name:
			self.name = name
		elif not self.name:
			raise RuntimeError("Unnamed object of '%s'" % (self.__class__.__name__,))
			
		if self.storage is None:
			raise RuntimeError("You didn't declare a storage for '%s'" % (self.__class__.__name__,))
		self.storage[name] = self

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


def get_collect(name, attr="list"):
	n = len(name)
	if not n:
		return None
	while n > 0:
		try:
			coll = collections[Name(name[:n])]
			c = coll.cls
			if n < len(name):
				coll = coll[Name(name[n:])]
			if not hasattr(c,attr):
				raise KeyError
			return coll

		except KeyError:
			n = n-1
	if n==0:
		raise RuntimeError("I could not find an entry for ‹› with '%s'." % (Name(name),attr))

def all_collect(attr="list"):
	for m in collections.itervalues():
		if hasattr(m,attr):
			yield m.name
