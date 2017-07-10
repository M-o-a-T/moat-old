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
from etcd_tree.node import EtcFloat,EtcBase, EtcDir, EtcString
import etcd
import inspect
import functools
from time import time
from traceback import format_exception
import weakref

from moat.types.etcd import recEtcDir
from . import webdef_names, WEBDEF_DIR,WEBDEF, WEBDATA_DIR,WEBDATA
from moat.util import do_async

import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

def template(template_name):
	def wrapper(func):
		@asyncio.coroutine
		@functools.wraps(func)
		def wrapped(*args, view=None, **kwargs):
			if asyncio.iscoroutinefunction(func):
				coro = func
			else:
				coro = asyncio.coroutine(func)
			context = yield from coro(*args, **kwargs)

			# Supports class based views see web.View
			try:
				response = render_string(template_name, view.request, context)
			except Exception as exc:
				logger.exception("%s: %s", template_name,context)
				return ""
			return response
		return wrapped
	return wrapper

class _DataLookup(object):
	"""Helper class to facilitate WebdefDir.data[]"""
	def __init__(self,wd):
		self.wd = wd
	def __getitem__(self, k):
		k = str(k).lower()
		v = self.wd['data'].get(k,_NOTGIVEN)
		if v is not _NOTGIVEN:
			return v

		p = self.wd.type
		while isinstance(p,WebdefDir):
			v = p['data'].get(k,_NOTGIVEN)
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

	async def init(self):
		"""Need to look up my type, and all its super-defs"""
		await super().init()
		t = await self.root.lookup(WEBDEF_DIR)
		if 'def' in self:
			tr = await t.lookup(self['def'])
			tr = await tr.lookup(WEBDEF)
			self.type = tr
		# TODO: hook up updater

	async def send_item(self,view, **kw):
		"""Send my data struct to this view"""
		id,pid = self.get_id()
		view.send_json(action="replace", id=id, parent=pid, data=await self.render(view=view))
	
	def render(self, view=None):
		if self._type is None:
			print("Rendering",self['def'])
			return self._render(view=view)
		return self._type.render(this=self, view=view)

	def recv_msg(self, act, view=None, **kw):
		if self._type is None:
			raise RuntimeError("No type known")
		self._type.recv_msg(act=act, this=self, view=view, **kw)

	@template('item.haml')
	def _render(self, level=1):
		id,pid = self.get_id()
		return dict(id=id,pid=pid, this=self)

	def get_id(self, level=1):
		id="f_%d" % self.parent._seq
		if level == 1:
			pid = "content"
		else:
			pid="f_%d" % self.parent.parent._seq
		return id,pid

class WebdataType(EtcString):
	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._type = None
		else:
			do_async(self._has_update)

	async def _has_update(self):
		print("Loading",self.value)
		p = self.parent
		if p is None:
			return
		p._type = await self.root.lookup(*(WEBDEF_DIR+tuple(self.value.split('/'))),name=WEBDEF)

#	@property
#	def param(self):
#		return _DataLookup(self)
#WebdataDir.register('timestamp',cls=EtcFloat)
WebdataDir.register('def',cls=WebdataType)

class WebpathDir(EtcDir):
	"""Directory for /web/PATH"""

	async def send_item(self,view, level=1, **kw):
		"""Send my data struct to this view"""
		id,pid = self.get_id(level)
		view.send_json(action="replace", id=id, parent=pid, data=await self.render(level, view=view))

	@template('dir.haml')
	def render(self, level=1):
		id,pid = self.get_id(level)
		return dict(id=id,level=level+2,pid=pid, this=self)

	def get_id(self,level):
		if level == 0:
			id="content"
			pid=""
		else:
			id="f_%d" % self._seq
			if level == 1:
				pid="content"
			else:
				pid="f_%d" % self.parent._seq
		return id,pid

WebpathDir.register(WEBDATA, cls=WebdataDir)
WebpathDir.register('*', cls=WebpathDir)

