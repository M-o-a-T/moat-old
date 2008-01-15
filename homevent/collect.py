# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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

"""Class to make storing collections of stuff simpler"""

from homevent.base import Name

from weakref import WeakValueDictionary,proxy

collections = WeakValueDictionary()


class Collection(dict):
	"""\
		This class implements named collections of things.

		Usage:
		
			class FooThings(Collection):
				name = "foo bar"
			FooThings = FooThings()

			class Foo(Collected):
				storage = FooThings.storage

		A subsequent "list foo bar" command enumerates all known Foo objects.

		"""

	def __repr__(self):
		try:
			return u"‹Collection %s›" % (self.__class__.__name__,)
		except Exception:
			return "<Collection:%s>" % (self.__class__.__name__,)

	def __init__(self):
		self._can_do = set(("list",))

		name = self.name
		if isinstance(name,basestring):
			name = name.split()
		name = Name(name)
		self.name = name
		if name in collections:
			return RuntimeError(u"A collection ‹%s› already exists" %(name,))
	
		collections[name] = self
	
	def does(self,name):
		assert name not in self._can_do
		self._can_do.add(name)

	def can_do(self,name):
		return name in self._can_do

	def iteritems(self):
		def name_cmp(a,b):
			return cmp(self[a].name,self[b].name)
		for k in sorted(self.iterkeys(),cmp=name_cmp):
			yield k,self[k]

	def itervalues(self):
		return sorted(super(Collection,self).itervalues())

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
	name = None

	def __init__(self, *name):
		if not name:
			name = self.name
		if not name:
			raise RuntimeError("Unnamed object of '%s'" % (self.__class__.__name__,))
			
		if self.storage is None:
			raise RuntimeError("You didn't declare a storage for '%s'" % (self.__class__.__name__,))

		self.name = name = Name(name)
		if name in self.storage:
			raise RuntimeError(u"Duplicate entry ‹%s› in ‹%s›" % (name,self.storage.name))

		super(Collected,self).__init__()
		self.storage[name] = self

	def __repr__(self):
		try:
			return u"‹Collected %s:%s›" % (self.__class__.__name__,self.name)
		except Exception:
			return "<Collected:%s>" % (self.__class__.__name__,)

	def list(self):
		"""Yield a couple of (left,right) tuples, for enumeration."""
		raise NotImplementedError("You need to override 'list' in '%s'" % (self.__class__.__name__,))

	def delete(self):
		"""Remove myself from a collection"""
		raise NotImplementedError("You need to override 'del' in '%s'" % (self.__class__.__name__,))

	def delete_done(self):
		del self.storage[self.name]

	def info(self):
		"""\
			Return a one-line string with additional data (but not the name!),
			if that makes sense.
			"""
		return None


class CKeyError(KeyError):
	def __init__(self,name,coll):
		self.name = name
		self.coll = coll
	def __repr__(self):
		return u"‹%s ‹%s› %s›" % (self.__class__.__name__, Name(self.name),self.coll)
	def __unicode__(self):
		return u"I could not find an entry for ‹%s› in %s." % (Name(self.name),self.coll)
	def __str__(self):
		return "I could not find an entry for ‹%s› in %s." % (Name(self.name),self.coll)


class CCollError(KeyError):
	def __init__(self,name):
		self.name = name
	def __repr__(self):
		return u"‹%s %s›" % (self.__class__.__name__, Name(self.name))
	def __unicode__(self):
		return u"‹%s› is a group, not an item." % (Name(self.name),)
	def __str__(self):
		return "‹%s› is a group, not an item." % (Name(self.name),)


def get_collect(name, allow_collection=False):
	c = None
	if not len(name):
		return None
	coll = collections

	while len(name):
		n = len(name)
		while n > 0:
			try:
				coll = coll[Name(name[:n])]
			except KeyError:
				n = n-1
			else:
				name = name[n:]
				if c is None: c = coll
				break

		if n == 0:
			try:
				coll = coll[name[0]]
			except KeyError:
				raise CKeyError(name,c)
			else:
				name = name[1:]
				if c is None: c = coll
	if not allow_collection and not isinstance(coll,Collected):
		raise CCollError(name)
	return coll

def all_collect(name="list"):
	def byname(a,b): return cmp(a.name,b.name)
	for m in sorted(collections.itervalues(),cmp=byname):
		if m.can_do(name):
			yield m
