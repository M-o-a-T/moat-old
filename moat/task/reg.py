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

"""\
This module handles per-task registration of callback functions and related
stuff.
"""

import asyncio
import weakref
import warnings
import attr
from inspect import iscoroutine

import logging
logger = logging.getLogger(__name__)

class DupRegError(RuntimeError):
	pass

@attr.s
class RegReg:
	func = attr.ib()
	release = attr.ib()
	weak = attr.ib(default=True)

def REG(cls, name, func, release, weak=True):
	"""\
		Register an allocate/free pair.

		Allocate:

		>>> releaser = await reg.@name(obj, …)

		calls obj.@func(…). The result (@res) is wrapped in a @release object.
		
		>>> await releaser.free()

		calls @res.@release(). The same thing happens when the registrar
		gets freed.

		If @release is a callable, it is called with the RegStore object as
		its sole argument. The original object is obtainable as @regstore.obj().
		The release method will not be called if the object no longer
		exists.

		Allocator and releaser will be awaited if necessary.

		The releaser will not be called if the object has already been
		freed. Set weak=False to prevent that from happening.
		"""
	try:
		r = cls._Reg__hooks
	except AttributeError:
		r = cls._Reg__hooks = {}
	for c in cls.__mro__:
		if name in getattr(c,'_Reg__hooks',{}):
			raise DupRegError(name,cls,c)

	r[name] = RegReg(func,release,weak)
	if not hasattr(Reg,name):
		def cb(self,obj,*a,**k):
			return self._reg(name,obj,*a,**k)
		setattr(Reg,name,cb)

class NoRegCallback(RuntimeError):
	"""\
		No named calback was found.
		"""
	pass

@attr.s
class _RegStore:
	"""\
		Saves a releaser for later freeing via Reg.release().
		"""
	obj = attr.ib()
	reg = attr.ib()
	thing=attr.ib()
	method=attr.ib()
	weak = attr.ib()

	@property
	def orig(self):
		obj = self.obj
		if self.weak:
			obj = obj()
		return obj

class RegStore(_RegStore):
	def __init__(self, obj, weak=True, **k):
		super().__init__(obj=weakref.ref(obj,self._released) if weak else obj, weak=weak, **k)

	async def release(self, _force=False):
		if not _force:
			if self not in self.reg.data:
				warnings.warn("%s: Released twice" % (repr(self),), stacklevel=2)
				return
			self.reg.data.remove(self)
		if callable(self.method):
			res = self.method(self)
		else:
			res = getattr(self.thing,self.method)()
		if iscoroutine(res):
			res = await res
		self.done = True
		return res

	def _released(self,_):
		"""\
			Called when the object itself gets deleted.
			In that case there is nothing more to release.
			"""
		if self in self.reg.data:
			self.reg.data.remove(self)
		
class Reg:
	"""\
		Registry for per-task objects which need to be freed when a task
		ends.
		"""
	def __new__(cls, task=None, loop=None):
		r = getattr(task,'moat_reg',None)
		if r is not None:
			return r
		return super(Reg,cls).__new__(cls)

	def __init__(self, task=None, loop=None):
		"""\
			Allocate a new registry.

			If @task is given, the tasks's registry is returned instead;
			if the task doesn't have a registry, a new one is allocated to it.
			"""
		self.data = set()
		if loop is None:
			loop = asyncio.get_event_loop()
		self.loop = loop
		if task is not None:
			self.task(task)
	
	async def _reg(self, name,obj, *a,**k):
		for c in obj.__class__.__mro__:
			r = getattr(c,'_Reg__hooks',None)
			if r is not None:
				r = r.get(name)
				if r is not None:
					break
		else:
			raise NoRegCallback(obj,name)
		res = getattr(obj, r.func)(*a,**k)
		if iscoroutine(res):
			res = await res
		res = RegStore(reg=self, obj=obj, thing=res, method=r.release, weak=r.weak)
		self.data.add(res)
		return res

	async def free(self):
		e = None
		while self.data:
			r = self.data.pop()
			try:
				await r.release(_force=True)
			except Exception as exc:
				logger.exception("Releasing %s",r)
			except BaseException as exc:
				e = exc

		if e is not None:
			raise e

	def task(self,f):
		t = asyncio.ensure_future(f, loop=self.loop)
		r = t.moat_reg
		if r is None:
			t.moat_reg = self
		elif r is not self:
			raise RuntimeError("Task already has storage",t)
		return t
	
	def __del__(self):
		assert not self.data

class Task(asyncio.Task):
	moat_reg = None
def makeTask(loop,coro):
	return Task(coro, loop=loop)
asyncio.get_event_loop().set_task_factory(makeTask)
