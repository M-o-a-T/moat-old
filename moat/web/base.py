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

##
# JSON methods:
# insert: new item, parent=target, id=id, data=HTML
#   no visuals (possibly TODO)
# replace: known item, id=id, keep=prefixes, data=HTML
#   items with id of [letter in prefix]+id are restored
#   no visuals
# update: id=id, data=HTML
#   visual, no restored sub-items
# delete: id=id,
#   visual

# On update:
# If the template has an "update" block, that block must contain one
# element with id=d+ID. If missing, the whole thing is replaced.
# If the template has a "reset" block, that block must contain one
# element with id=r+ID. If missing, nothing will happen.

##
# Data methods:
#  >feed_subdir(view) => called on new top-level, responsible for calling add_item
#  >send_insert(view, level)
#  >send_update(view, level)
#  >send_delete(view, level)

## View methods:
#  send_json(**kw)
#  key_for(item) => ID
# >add_item => will call send_insert
#  get_level(item) => level# for this, or KeyError if unknown

# '>' is async

import asyncio
from aiohttp_jinja2 import web,render_string, get_env
from aiohttp.web import HTTPInternalServerError
from etcd_tree.etcd import EtcTypes, WatchStopped
from etcd_tree.node import EtcFloat,EtcBase, EtcDir,EtcAwaiter, EtcString,EtcInteger
import etcd
import inspect
import functools
from time import time
from traceback import format_exception
import weakref
import blinker
from collections.abc import Mapping

from moat.types.etcd import recEtcDir
from . import webdef_names, WEBDEF_DIR,WEBDEF, WEBDATA_DIR,WEBDATA, WEBCONFIG
from moat.util import do_async
from moat.dev import DEV_DIR,DEV

import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

def get_template(app, template_name):
	"""Helper to fetch a template"""
	env = get_env(app)
	try:
		return env.get_template(template_name)
	except (KeyError, jinja2.TemplateNotFound) as e:
		raise HTTPInternalServerError(text="Template '{}' not found".format(template_name)) from e

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

		p = self.wd._type
		while isinstance(p,WebdefDir):
			v = p.get(k,_NOTGIVEN)
			if v is not _NOTGIVEN:
				return v

			try:
				p = p.parent.parent.lookup(WEBDEF)
			except IndexError:
				break
		raise KeyError(k)

class WebdefBase(object):
	"""\
		Base class to handle template reading and context building

		This class applies to the :item entry. Thus it will replace the
		parent's "entry_id" div (see templates/dir.haml).
	
		"""
	TEMPLATE = "item.haml"

	def get_template(self, item, view, level=1):
		return get_template(view.request.app, self.TEMPLATE)

	def get_context(self, item, view, level=1):
		key = view.key_for(item)
		par = view.key_for(item.parent)
		return dict(
			level=level,
			id='d'+par, ## my top level
			parent_id=par,
			view=view,
			item=item,
			update_id='d'+key, ## data, visually updated
			reset_id='r'+key,  ## UI, not visually updated
		)

	def render(self, view, level, ctx, item=None):
		if item is None:
			iem = self
		t = self.get_template(item=item,view=view,level=level)
		return t.render(ctx)

DefaultConfig = {
	'order': 0,
}

class ConfigDict(Mapping):
	def __init__(self,parent):
		self.parent = weakref.ref(parent)
	def __getitem__(self,k):
		p = self.parent()
		if p is not None:
			cf = p.get(WEBCONFIG,None)
			if cf is not None:
				v = cf.get(k,None)
				if v is not None:
					return v
		pcf = getattr(p.parent,'config',None)
		if pcf is not None:
			return pcf.get(k)
		return DefaultConfig[k]
	def __iter__(self):
		while False:
			yield None
	def __len__(self):
		return 0

	
class WebpathDir(WebdefBase, EtcDir):
	"""Directory for /web/PATH"""
	TEMPLATE = "dir.haml"
	_propagate_updates = False

	def get_context(self, view, level=1):
		kw = super().get_context(self,view,level)
		key = view.key_for(self)
		par = view.key_for(self.parent)

		n_sub = n_entry = 0
		for k in self.keys():
			if k[0] != ':':
				n_sub += 1
			elif k == WEBDATA:
				n_entry += 1

		kw.update(
			id=key,
			entry_id='d'+key,
			content_id='c'+key,
			parent_id='c'+par,
			n_sub=n_sub,
			n_entry=n_entry,
		)
		del kw['update_id']
		del kw['reset_id']
		return kw

	updates = None
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self.updates = blinker.Signal()

	async def init(self):
		if WEBCONFIG in self:
			await self[WEBCONFIG]
		await super().init()

	@property
	def config(self):
		return ConfigDict(self)

	async def feed_subdir(self, view, level=0):
		await view.add_item(self, level)
		for v in self.values():
			if isinstance(v,EtcAwaiter):
				v = await v

			fs = getattr(v,'feed_subdir',None)
			if fs is not None:
				await fs(view, level+1)
		
	def has_update(self):
		self.updates.send(self)
		if self.is_new and hasattr(self.parent,'updates'):
			self.parent.updates.send(self)

	async def send_insert(self,view, level, **_kw):
		"""Send my data struct to this view"""
		kw = self.get_context(view,level)
		data = self.render(level=level, view=view, ctx=kw)
		if level == 0:
			view.send_json(action="replace", id=kw['id'], data=data)
		else:
			view.send_json(action="insert", id=kw['id'], parent=kw['parent_id'], data=data, sortkey="%04d%s" % (self.config['order']+5000,self.name))

	async def send_update(self,view,level, **_kw):
		kw = self.get_context(view,level)
		try:
			_level = view.get_level(self)
		except KeyError:
			try:
				assert level > 0
				_level = view.get_level(self.parent)
			except KeyError:
				logger.debug("No pkey, render later: %s",self)
				return 
			assert _level == level-1
			self.feed_subdir(view,level=level)
		else:
			assert level == _level
			kw = self.get_context(view,level)
			data = self.render(level=level, view=view, ctx=kw)
			view.send_json(action="replace", id=kw['id'], keep="cd", data=data)

	async def send_delete(self,view,level, **_kw):
		kw = self.get_context(view,level)
		view.send_json(action="delete", id=kw['id'])

class WebdefDir(WebdefBase,recEtcDir,EtcDir):
	"""Directory for /meta/web/PATH/:def - A class linking a webdef to its etcd entry
		Linked into /meta in moat.types.etcd"""

	@classmethod
	async def this_obj(cls, parent=None,recursive=None, pre=None, **kw):
		if recursive is None:
			raise ReloadData
		m = webdef_names()['/'.join(parent.path[len(WEBDEF_DIR):])]
		res = m(parent=parent,pre=pre,**kw)
		return res

class WebdataDir(recEtcDir,EtcDir):
	"""Directory for /web/PATH/:item"""
	_type = None
	_value = None
	mon = None # value monitor
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
		else:
			self._type = WebdefBase() # gaah
		if 'value' in self:
			tr = await self.root.lookup(DEV_DIR)
			tr = await tr.lookup(self['value'])
			tr = await tr.lookup(DEV)
			self._value = tr

	@property
	def data(self):
		return _DataLookup(self)

	async def feed_subdir(self, view, level=0):
		await view.add_item(self, level)

	def get_template(self,*a,**kw):
		return self._type.get_template(self, *a,**kw)

	def get_context(self,*a,**kw):
		return self._type.get_context(self, *a,**kw)

	async def send_insert(self,view, level, **_kw):
		"""Send my data struct to this view"""
		assert level > 0
		kw = self.get_context(view=view, level=level)
		data = self.render(level=level, view=view, ctx=kw)
		view.send_json(action="replace", id=kw['id'], parent=kw['parent_id'], data=data)

	async def send_update(self, view,level, full=False,**_kw):
		template = self.get_template(view=view,level=level)
		kw = self.get_context(view=view,level=level)
		data = self.render(view,level, ctx=kw)

		updater = None if full else template.blocks.get('update',None)
		if updater is None:
			data = template.render(kw)
			if view.values.get(kw['id'],"") != data:
				view.send_json(action="update", id=kw['id'], data=data)
				view.values[kw['id']] = data
		else:
			ctx = template.new_context(kw)
			data = ''.join(updater(ctx))
			if view.values.get(kw['update_id'],"") != data:
				view.send_json(action="update", id=kw['update_id'], data=data)
				view.values[kw['update_id']] = data
			resetter = template.blocks.get('reset',None)
			if resetter is not None:
				data = ''.join(resetter(ctx))
				view.send_json(action="replace", id=kw['reset_id'], data=data)

	async def send_delete(self,view,level, **_kw):
		kw = self.get_context(view=view,level=level)
		view.send_json(action="clear", id=kw['id'])

	def render(self, *a,**kw):
		"""Calls self._type.render()"""
		return self._type.render(item=self, *a,**kw)

	def recv_msg(self, act, view, **kw):
		if self._type is None:
			view.send_json(action="error", msg = act+": No type for "+'/'.join(self.path))
			return

		self._type.recv_msg(act=act, item=self, view=view, **kw)

	def has_update(self):
		super().has_update()
		self.updates.send(self, full=True)
		if self.is_new and hasattr(self.parent,'updates'):
			self.parent.updates.send(self)
		elif self.is_new is None:
			self.updates.send(self)
			if self.mon is not None:
				self.mon.cancel()
				self.mon = None

	def update_value(self,val):
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
			p._type = WebdefBase()
		else:
			p._type = self.root.lookup(*(WEBDEF_DIR+tuple(self.value.split('/'))),name=WEBDEF)

class WebdataValue(EtcString):
	"""Value path for WebdataDir"""
	_propagate_updates=False
	_update_delay = 0.01
	_reset_delay_job = None

	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._value = None
			if p.mon is not None:
				p.mon.cancel()
		else:
			self._update_delay = 1
			if self._reset_delay_job is not None:
				self._reset_delay_job.cancel()
			self._reset_delay_job = self._loop.call_later(1, self._reset_delay)

			do_async(self._has_update)

	def _reset_delay(self):
		self._reset_delay_job = None
		self._update_delay = 0.01

	async def _has_update(self):
		p = self.parent
		if p is None:
			return
		if p.mon is not None:
			p.mon.cancel()
		p._value = await self.root.lookup(*(DEV_DIR+tuple(self.value.split('/'))),name=DEV)
		p.mon = p._value.add_monitor(p.update_value)
		p.update_value(p._value)

class WebconfigDir(EtcDir):
	pass
WebconfigDir.register('order', cls=EtcInteger)

#	@property
#	def param(self):
#		return _DataLookup(self)
#WebdataDir.register('timestamp',cls=EtcFloat)
WebdataDir.register('def',cls=WebdataType)
WebdataDir.register('value',cls=WebdataValue)
WebdefDir.register('timestamp',cls=EtcFloat)
WebdefDir.register('created',cls=EtcFloat)
WebpathDir.register(WEBDATA, cls=WebdataDir)
WebpathDir.register('*', cls=WebpathDir)
WebpathDir.register(WEBCONFIG, cls=WebconfigDir)

