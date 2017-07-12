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

"""
Class for managing web data snippets.
"""

import asyncio
from aiohttp_jinja2 import web,render_string
from etcd_tree.etcd import EtcTypes, WatchStopped
from etcd_tree.node import EtcFloat,EtcBase, EtcDir,EtcAwaiter, EtcString
import etcd
import inspect
import functools
from time import time
from traceback import format_exception
import weakref
import blinker

from moat.types.etcd import recEtcDir
from . import webdef_names, WEBDEF_DIR,WEBDEF, WEBDATA_DIR,WEBDATA
from moat.util import do_async
from moat.dev import DEV_DIR,DEV

import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

def template(template_name=None):
	"""\
		Decorator to apply the result to a template.
		The decorated function may or may not be a coroutine.
		If no template_name is given, assume that the context includes it.

		>>> @template ## @template() also works
		>>> def render(**kw):
		>>>    return { 'template_name': 'foo.html' }

		is equivalent to

		>>> @template('foo.html')
		>>> def render(**kw):
		>>>    return { }

		"""
	def wrapper(func):
		@asyncio.coroutine
		@functools.wraps(func)
		def wrapped(*args, view=None, **kwargs):
			if asyncio.iscoroutinefunction(func):
				coro = func
			else:
				coro = asyncio.coroutine(func)
			context = yield from coro(*args, view=view, **kwargs)

			if template_name is None:
				tmpl = context.pop('template_name')
			else:
				tmpl = template_name

			# Supports class based views see web.View
			try:
				response = render_string(tmpl, view.request, context)
			except Exception as exc:
				logger.exception("%s: %s", template_name,context)
				return ""
			return response
		return wrapped

	if callable(template_name):
		f = template_name
		template_name = None
		return wrapper(f)
	else:
		return wrapper

class _DataLookup(object):
	"""Helper class to facilitate WebdefDir.data[]"""
	def __init__(self,wd):
		self.wd = wd
	def __getitem__(self, k):
		k = str(k).lower()
		v = self.wd.get(k,_NOTGIVEN)
		if v is not _NOTGIVEN:
			return v

		p = self.wd.type
		while isinstance(p,WebdefDir):
			v = p.get(k,_NOTGIVEN)
			if v is not _NOTGIVEN:
				return v

			try:
				p = p.parent.parent.lookup(WEBDEF)
			except IndexError:
				break
		raise KeyError(k)

class WebdefDir(recEtcDir,EtcDir):
	"""Directory for /meta/web/PATH/:def - A class linking a webdef to its etcd entry
		Linked into /meta in moat.types.etcd"""
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._type = webdef_names()['/'.join(self.path[len(WEBDEF_DIR):-1])]
		self._type.types(self)
	
	@classmethod
	async def this_obj(cls, parent=None,recursive=None, pre=None, **kw):
		if recursive is None:
			raise ReloadData
		m = webdef_names()['/'.join(parent.path[len(WEBDEF_DIR):])]
		res = m(parent=parent,pre=pre,**kw)
		return res

	@classmethod
	def types(cls,types):
		pass

	@property
	def data(self):
		return _DataLookup(self)

WebdefDir.register('timestamp',cls=EtcFloat)
WebdefDir.register('created',cls=EtcFloat)

class WebdataDir(recEtcDir,EtcDir):
	"""Directory for /web/PATH/:item"""
	_type = None
	_value = None
	_mon = None # value monitor
	updates = None # signal: updated value

	def __init__(self,*a,**k):
		self.updates = blinker.Signal()
		super().__init__(*a,**k)

	async def init(self):
		"""Need to look up my type, and all its super-defs"""
		await super().init()
		if 'def' in self:
			tr = await self.root.lookup(WEBDEF_DIR)
			tr = await tr.lookup(self['def'])
			tr = await tr.lookup(WEBDEF)
			self._type = tr
		if 'value' in self:
			tr = await self.root.lookup(DEV_DIR)
			tr = await tr.lookup(self['value'])
			tr = await tr.lookup(DEV)
			self._value = tr

	async def feed_subdir(self, view, level=0):
		await view.add_item(self, level)

	async def send_item(self,view, **kw):
		"""Send my data struct to this view"""
		id = view.key_for(self)
		pid = view.key_for(self.parent)
		view.send_json(action="replace", id=id, parent=pid, data=await self.render(view=view))
	
	def render(self, view=None, **kw):
		"""coroutine!"""
		if self._type is None:
			print("Rendering",self,self['def'])
			return self._render(view=view, **kw)
		return self._type.render(this=self, view=view, **kw)

	def recv_msg(self, act, view, **kw):
		if self._type is None:
			view.send_json(action="error", msg = act+": No type for "+'/'.join(self.path))
			return

		self._type.recv_msg(act=act, this=self, view=view, **kw)

	@template('item.haml')
	def _render(self, view=None, level=1, **kw):
		id,pid = self.get_id(view)
		return dict(id=id,pid=pid, this=self)

	def get_id(self, view):
		id = view.key_for(self)
		pid = "" if id == "content" else view.key_for(self.parent)
		return id,pid
	
	def has_update(self):
		super().has_update()
		if self.is_new is None and self._mon is not None:
			self._mon.cancel()
			self._mon = None

	def update_value(self,val):
		#print("HAS",val,self,self.mon)
		key = self.get('subvalue','value').split('/')
		for k in key[:-1]:
			if k:
				val = val.get(k)
		key = key[-1]
		if key:
			val = getattr(val,key)
		self.updates.send(self, value=val)

class WebdataType(EtcString):
	"""Type path for WebdataDir"""
	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._type = None
		else:
			do_async(self._has_update)

	async def _has_update(self):
		print("Using",self.value)
		p = self.parent
		if p is None:
			return
		p._type = await self.root.lookup(*(WEBDEF_DIR+tuple(self.value.split('/'))),name=WEBDEF)
		print("Using",p,self.value,p._type)

class WebdataValue(EtcString):
	"""Value path for WebdataDir"""
	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._value = None
		else:
			do_async(self._has_update)

	async def _has_update(self):
		print("Load from",self.value)
		p = self.parent
		if p is None:
			return
		p._value = await self.root.lookup(*(DEV_DIR+tuple(self.value.split('/'))),name=DEV)
		p.mon = p._value.add_monitor(p.update_value)
		p.update_value(p._value)
		pass

#	@property
#	def param(self):
#		return _DataLookup(self)
#WebdataDir.register('timestamp',cls=EtcFloat)
WebdataDir.register('def',cls=WebdataType)
WebdataDir.register('value',cls=WebdataValue)

class WebpathDir(EtcDir):
	"""Directory for /web/PATH"""

#	updates = None
#	def __init__(self,*a,**k):
#		super().__init__(*a,**k)
#		self.updates = blinker.Signal()
#
	async def feed_subdir(self, view, level=0):
		await view.add_item(self, level)
		for v in self.values():
			if isinstance(v,EtcAwaiter):
				v = await v

			fs = getattr(v,'feed_subdir',None)
			if fs is not None:
				await fs(view, level+1)
		
	async def send_item(self,view, level=1, **kw):
		"""Send my data struct to this view"""
		id,pid = self.get_id(view)
		view.send_json(action="replace", id=id, parent=pid, data=await self.render(level=level, view=view))

#	def has_update(self):
#		if self._is_new is not True:
#			return
#		self.updates.send(self, value=val)

	def get_id(self,view):
		id = view.key_for(self)
		pid = "" if id == "content" else view.key_for(self.parent)
		return id,pid

	@template('dir.haml')
	def render(self, view=None, level=1, **kw):
		id,pid = self.get_id(view)
		n_sub = n_entry = 0
		for k in self.keys():
			if k[0] != ':':
				n_sub += 1
			elif k == WEBDATA:
				n_entry += 1

		return dict(id=id,level=level+2,pid=pid, this=self, n_sub=n_sub, n_entry=n_entry)

WebpathDir.register(WEBDATA, cls=WebdataDir)
WebpathDir.register('*', cls=WebpathDir)

