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
		"""A simple way to create a stacked clone"""
		c = Context(self,**k)
		if ctx is not None:
			if self in ctx._parents():
				c = Context(ctx,**k) # duh
			elif ctx not in self._parents():
				c._parent.insert(0,ctx)
		return c

	def _parents(self):
		for p in self._parent:
			yield p
			for pp in p._parents():
				yield pp
		
	def __getattribute__(self,key):
		if key.startswith("_"):
			return super(Context,self).__getattribute__(key)
		store = self._store
		if key in store:
			r = store[key]
		else:
			r = VanishedAttribute
			for p in self._parent:
				try:
					r = getattr(p,key)
				except KeyError:
					pass
				else:
					break
		if r is VanishedAttribute:
			raise KeyError(self,key)
		try: r = r.value
		except AttributeError: pass
		return r

	def __setattr__(self,key,val):
		if key.startswith("_"):
			return super(Context,self).__setattr__(key,val)
		try:
			s = self._store[key]
			s.value = val
		except (KeyError, AttributeError):
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

