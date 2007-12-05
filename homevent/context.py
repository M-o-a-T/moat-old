# -*- coding: utf-8 -*-
"""\
	This module holds a Context object.

	A Context object is something with attributes that stacks its values.
	See test/context.py for usage examples.
	"""

import sys

class VanishedAttribute: pass

class Context(object):
	"""A stackable context type of thing."""
	def __init__(self,parent=None,**k):
		if parent is not None:
			self._parent = [parent]
		else:
			self._parent = []
		self._store = {}
		self._store.update(**k)

	def __call__(self,ctx=None,**k):
		"""Create a clone with an additional parent context"""
		if ctx is None:
			c = Context(self,**k)
		elif self in ctx._parents():
			c = Context(ctx,**k)
		else:
			c = Context(self,**k)
			if ctx not in self._parents():
				c._parent.append(ctx)
		return c

	def _parents(self):
		pl = self._parent[:]
		while pl:
			p = pl.pop(0)
			yield p
			pl.extend(p._parent)
		
	def __getattribute__(self,key):
		if key.startswith("_"):
			return super(Context,self).__getattribute__(key)
		store = self._store
		if key in store:
			r = store[key]
		else:
			r = VanishedAttribute
			for p in self._parents():
				try:
					r = p._store[key]
				except KeyError:
					pass
				else:
					break
		if r is VanishedAttribute:
			raise KeyError(self,key)
		return r

	def __setattr__(self,key,val):
		if key.startswith("_"):
			return super(Context,self).__setattr__(key,val)
		self._store[key] = val

	def __delattr__(self,key):
		if key.startswith("_"):
			return super(Context,self).__delattr__(key)
		self._store[key] = VanishedAttribute

	def __contains__(self,key):
		store = self._store
		if key in store: return store[key] is not VanishedAttribute
		for p in self._parent:
			if key in p:
				return True
		return False
	
	def __nonzero__(self):
		if bool(self._store):
			return True
		for p in self._parent:
			if bool(p):
				return True
		return False
	
	def __repr__(self):
		res = ""
		for p in self._parent:
			if res != "":
				res += ","
			res += repr(p)
		store = self._store
		if store:
			if res != "":
				res += ","
			res += repr(store)
		return "Ctx(%s)" % (res,)
	
	def _dump_get(self,n):
		from homevent.logging import log,DEBUG
		log(DEBUG,"CTX:",n,"is",getattr(self,n))
		self._dump_tree("")
	def _dump_tree(self,pre):
		from homevent.logging import log,DEBUG
		log(DEBUG,"CTX "+pre,unicode(self._store))
		for p in self._parent:
			p._dump_tree(pre+"  ")


def default_context(ctx,**defaults):
	"""\
		Create a new context with default content.

		For all keys not in the original context, call the function
		that's in k for that key and set the content to that.
		"""
	todo = {}
	if ctx is not None:
		for k,v in defaults.items():
			if k not in ctx:
				todo[k]=v()
	else:
		for k,v in defaults.items():
			todo[k]=v()
	if todo or ctx is None:
		if ctx is None: ctx = Context
		ctx = (ctx or Context)(**todo)
	return ctx

