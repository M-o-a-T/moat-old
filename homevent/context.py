# -*- coding: utf-8 -*-
"""\
	This module holds a Context object.

	A Context object is something with attributes that stacks its values.
	See test/context.py for usage examples.
	"""

class VanishedAttribute: pass

class Context(object):
	"""A stackable context type of thing."""
	def __init__(self,parent=None,**k):
		self._parent = parent
		self._store = {}
		self._store.update(**k)

	def __call__(self,**k):
		"""A simple way to create a stacked clone"""
		return Context(self,**k)

	def __getattribute__(self,key):
		if key.startswith("_"):
			return super(Context,self).__getattribute__(key)
		store = self._store
		if key in store:
			r = store[key]
		else:
			parent = self._parent
			if parent:
				r = getattr(parent,key)
			else:
				raise KeyError(self,key)
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
		parent = self._parent
		return parent and key in parent
	
	def __nonzero__(self):
		return bool(self._store) or bool(self._parent)
	
	def __repr__(self):
		parent = self._parent
		if parent:
			res = repr(self._parent)
		else:
			res = ""
		store = self._store
		if store:
			if parent:
				return "Ctx(%s,%s)" % (res,repr(store))
			else:
				return "Ctx(%s)" % (repr(store),)
		else:
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

