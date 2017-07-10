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
from etcd_tree.node import EtcFloat,EtcBase, EtcDir
import etcd
import inspect
import functools
from time import time
from traceback import format_exception
import weakref

from moat.types.etcd import recEtcDir
from . import webdef_names, WEBDEF_DIR,WEBDEF, WEBDATA_DIR,WEBDATA

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
            response = render_string(template_name, view.request, context)
            return response
        return wrapped
    return wrapper

class _DataLookup(object):
	"""Helper class to facilitate WebDef.data[]"""
	def __init__(self,wd):
		self.wd = wd
	def __getitem__(self, k):
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
	"""A class linking a webdef to its etcd entry"""
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._type = webdef_names()['/'.join(self.path[len(WEBDEF_DIR):-1])]
		self._type.types(self)
	
	async def init(self):
		await super().init()
		t = await self.root.lookup(WEBDEF_DIR)
		p = self.parent.parent
		if t != t:
			p = await p.lookup(WEBDEF)
			# TODO: hook up updater
		
WebdefDir.register('timestamp',cls=EtcFloat)
WebdefDir.register('created',cls=EtcFloat)

class WebdataDir(recEtcDir,EtcDir):
	"""A class linking a web entry to its data, display, etc."""
	type = None

	async def init(self):
		"""Need to look up my type, and all its super-defs"""
		await super().init()
		t = await self.root.lookup(WEBDEF_DIR)
		if 'def' in self:
			tr = await t.lookup(self['def'])
			tr = await tr.lookup(WEBDEF)
			self.type = tr
		# TODO: hook up updater

	async def send_item(self,view, level=0):
		"""Send my data struct to this view"""
		id,pid = self.get_id(level)
		view.send_json(action="replace", id=id, parent=pid, data='<div>Item %s %s!</div>' % (id,pid,))

	def get_id(self,level):
		if level == 0:
			id="content"
			pid=""
		else:
			id="f_%d" % self.parent._seq
			if level == 1:
				pid="content"
			else:
				pid="f_%d" % self.parent.parent._seq
		return id,pid

#	@property
#	def param(self):
#		return _DataLookup(self)
#WebdataDir.register('timestamp',cls=EtcFloat)
#WebdataDir.register('created',cls=EtcFloat)

class WebpathDir(EtcDir):
	"""A class linking web entries to their data, display, etc."""

	async def send_item(self,view, level=1):
		"""Send my data struct to this view"""
		id,pid = self.get_id(level)
		level += 2
		view.send_json(action="replace", id=id, parent=pid, data=await self.render(level, view=view))

	@template('dir.haml')
	def render(self, level=1):
		id,pid = self.get_id(level)
		return dict(id=id,level=level+2,pid=pid)

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

class WebDef(object):
	"""\
		I am the base class for a web data snippet.

		I can render a single datum, and accept events to manipulate it.
		"""
	name = None # a type name
	summary = """This is a prototype. Do not use."""
	schema = {}
	doc = None

	def __init__(self, cmd, webdir=None, **cfg):
		self.cmd = cmd
		self.name = name
		self.dir = webdir
		# TODO: hook up updater

	@classmethod
	def types(cls,types):
		pass

	@property
	def cfg(self):
		return self.dir.data

	@template('unknown.haml')
	def render(self):
		"Override me!"
		return {'path': self.dir.path, 'cls': self.__class__.__name__}

class WebDir(WebDef):
	"""\
		I render a directory.
		"""
	def __init__(self, cmd, webdir=None, **cfg):
		super().__init__(cmd, webdir=webdir, **cfg)
	
	@template('dir.haml')
	def render(self):
		return {'path': self.dir.path}

