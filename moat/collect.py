# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""Class to make storing collections of stuff simpler"""

import six

from moat.base import Name,SName
from moat.check import Check
from moat.context import Context

from weakref import WeakValueDictionary,proxy

collections = WeakValueDictionary()

class Collection(dict):
	"""\
		This class implements named collections of things.

		Usage:
		
			class FooThings(Collection):
				name = "foo bar"
			FooThings = FooThings()
			FooThings.does("del")

			class Foo(Collected):
				storage = FooThings.storage

		A subsequent "list foo bar" command enumerates all known Foo objects.

		"""
	prio = 0 # the order to de-allocate everything on shutdown
	exists = None

	def __repr__(self):
		try:
			return u"‹Collection %s›" % (self.__class__.__name__,)
		except Exception:
			return "<Collection:%s>" % (self.__class__.__name__,)

	def __new__(cls):
		self = dict.__new__(cls)

		name = SName(self.name)
		if name in collections:
			return collections[name]

		self.name = name

		self._can_do = set()
		self.does("list")

		collections[name] = self
		return self

	def __init__(self):
		if self.exists is None:
			class ExistsCheck(Check):
				name=Name("exists",*self.name)
				doc="check if a named %s object exists"%(self.name,)
				def check(xself,*args):
					if not len(args):
						raise SyntaxError(u"Usage: if exists %s ‹name…›" %(" ".join(self.name),))
					oname = Name(*args)
					return oname in self
			self.exists = ExistsCheck
			self.exists.__name__ = str("ExistsCheck_"+"_".join(self.name))
	
	def does(self,name):
		name = SName(name)
		assert name not in self._can_do
		self._can_do.add(name)

	def exists_check(self):
		return ExistsCheck

	def can_do(self,name):
		name = SName(name)
		return name in self._can_do

	def items(self):
		for k in sorted(self.keys(), key=lambda x:self[x].name):
			yield k,self[k]

#	def values(self):
#		return sorted(super(Collection,self).values())

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
	_ectx = None # event context

	def __init__(self, *name):
		if not name:
			name = self.name
		if not name:
			raise RuntimeError("Unnamed object of '%s'" % (self.__class__.__name__,))
			
		if self.storage is None:
			raise RuntimeError("You didn't declare a storage for '%s'" % (self.__class__.__name__,))

		self.name = name = SName(name)
		if name in self.storage:
			self.dup_error(name)

		super(Collected,self).__init__()
		self.storage[name] = self
		self._ectx = Context()

	@property
	def ectx(self):
		self.update_ectx()
		return self._ectx
	def update_ectx(self):
		pass

	def dup_error(self,name):
		raise RuntimeError(u"Duplicate entry ‹%s› in ‹%s›" % (name,self.storage.name))

	def __repr__(self):
		try:
			return u"‹Collected %s:%s›" % (self.__class__.__name__,self.name)
		except Exception:
			return "<Collected:%s>" % (self.__class__.__name__,)

	def list(self):
		"""Yield a couple of (left,right) tuples, for enumeration."""
		yield (six.text_type(self),)
		yield ("name",self.name)

		s = super(Collected,self)
		if hasattr(s,'list'): yield s

	def delete(self, ctx=None):
		"""Remove myself from a collection"""
		del self.storage[self.name]

	def info(self):
		"""\
			Return a one-line string with additional data (but not the name!),
			if that makes sense.
			"""
		return None

@six.python_2_unicode_compatible
class CKeyError(KeyError):
	def __init__(self,name,coll):
		self.name = name
		self.coll = coll
	def __repr__(self):
		return u"‹%s ‹%s› %s›" % (self.__class__.__name__, SName(self.name),self.coll)
	def __str__(self):
		return u"I could not find an entry for ‹%s› in %s." % (SName(self.name),self.coll)

@six.python_2_unicode_compatible
class CCollError(KeyError):
	def __init__(self,name):
		self.name = name
	def __repr__(self):
		return u"‹%s %s›" % (self.__class__.__name__, SName(self.name))
	def __str__(self):
		return u"‹%s› is a group, not an item." % (SName(self.name),)

def get_collect(name, allow_collection=False):
	c = None
	if not len(name):
		return None
	coll = collections

	if allow_collection and name[-1] == "*":
		return coll[Name(*name[:-1])]
	while len(name):
		n = len(name)
		while n > 0:
			try:
				coll = coll[Name(*name[:n])]
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
				from moat.logging import DEBUG,log
				log(DEBUG,"Contents: "+", ".join(str(x) for x in coll.keys()))
				raise CKeyError(name,coll)
			else:
				name = name[1:]
				if c is None: c = coll
	if not allow_collection and not isinstance(coll,Collected):
		raise CCollError(name)
	return coll

def all_collect(name="list", skip=False):
	for m in sorted(collections.values(), key=lambda x:x.name):
		if skip and not m:
			continue
		if m.can_do(name):
			yield m

### There's also a helper which cleans out all collections
### see moat.reactor.Shutdown_Collections
