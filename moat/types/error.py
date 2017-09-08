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

import asyncio
from weakref import WeakValueDictionary
from pprint import pformat
from time import time

from qbroker.util import import_string
from etcd_tree import EtcRoot, EtcDir, EtcString, EtcInteger, EtcFloat, EtcXValue, ReloadRecursive, EtcAwaiter
from etcd_tree.node import DummyType

import logging
logger = logging.getLogger(__name__)

from . import ERROR_DIR
from .etcd import recEtcDir

# This file contains all "singleton" etcd directories, i.e. those with
# fixed names at the root of the tree

class ErrorLoc(EtcXValue):
	"""Holds the location of an error, at /status/error/TAG/UNIQ/loc"""
	ptr = None
	async def get_ptr(self):
		if self.ptr is None:
			try:
				self.ptr = await self.root.lookup(self.value)
			except KeyError:
				logger.debug("Error with invalid location: %s > %s",self,self.value)
				pass
		return self.ptr

class ErrorRecord(recEtcDir,EtcDir):
	"""Holds an error record, at /status/error/TAG/UNIQ"""
	async def get_ptr(self):
		loc = self.get('loc',None)
		if loc is not None:
			loc = await loc.get_ptr()
		else:
			logger.debug("Error without location: %s",self)
		return loc

	async def delete(self, both=True):
		if both:
			ptr = await self.get_ptr()
			if ptr is not None:
				await ptr.delete(both=False)
		p = self.parent
		await super().delete(recursive=True)
		if p is not None and not len(p):
			await p.delete()
	
	async def verify(self, delete=True):
		"""Check that this is a valid error record."""
		valid = False
		p = await self.get_ptr()
		if p is not None:
			valid = True
			try:
				loc = p['error'][self.parent.name]
			except KeyError:
				logger.debug("Error without reverse: %s > %s",self,p)
				valid = False
			else:
				if loc.value != self.name:
					logger.debug("Error with wrong reverse: %s > %s", self,loc)
					valid = False

		if not valid and delete:
			await self.delete(both=False)
		return valid

ErrorRecord.register('loc', cls=ErrorLoc)
ErrorRecord.register('msg', cls=EtcString)
ErrorRecord.register('counter', cls=EtcInteger)
ErrorRecord.register('timestamp', cls=EtcFloat)

class ErrorPtr(EtcXValue):
	"""Holds the pointer to an error"""
	error = None
	async def delete(self, both=True):
		if both and self.ptr is not None:
			try:
				await self.ptr.delete(both=False)
			except KeyError:
				return
		p = self.parent
		await super().delete()
		if p is not None and not len(p):
			await p.delete()

	async def init(self):
		try:
			self.ptr = await self.root.lookup(ERROR_DIR+(self.name,self.value))
		except KeyError:
			self.ptr = None

			logger.error("Error record at %s not found", '/'.join(self.path))
			p = self.parent
			await self.delete()
		
	def has_update(self):
		if self.is_new is None:
			self.root.task(self.delete())
		super().has_update()

	
class hasErrorDir:
	"""an etcd mix-in which manages error messages"""

	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._error_lock = asyncio.Lock(loop=self._loop)

	async def init(self):
		await super().init()
		e = self.get('error',None)
		if type(e) is EtcAwaiter:
			await e.load(recursive=True)

	async def _hasError_err(self, tag, create=None):
		return (await self.root.subdir(ERROR_DIR, name=tag, create=create))

	def subtype(self,*path,raw=False,**kw):
		if len(path) == 2 and path[0] == "error":
			return DummyType(ErrorPtr) if raw else ErrorPtr
		return super().subtype(*path,raw=raw,**kw)

	async def set_error(self, tag, msg, **kw):
		async with self._error_lock:
			try:
				e = await self['error'][tag]
			except KeyError:
				pass
			else:
				ptr = await e.ptr
				if ptr is not None:
					await ptr.set('msg',msg)
					await ptr.set('counter',ptr.get('counter',1)+1)
					await ptr.set('timestamp',time())
					return

			t = await self.root.subdir(ERROR_DIR, name=tag)
			kw['loc'] = '/'.join(self.path)
			kw['msg'] = msg
			kw['timestamp'] = time()
			v = await t.set(None,kw)
			v = t[v[0]]
			await self.set('error',{tag:v.name})
			return v

	async def clear_error(self, tag):
		async with self._error_lock:
			try:
				v = self['error'][tag]
			except KeyError:
				return
			await v.delete()

