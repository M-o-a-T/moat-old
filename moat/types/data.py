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

from etcd_tree.node import EtcString,EtcInteger,EtcFloat,EtcBoolean, EtcDir,EtcXValue,EtcValue
from etcd_tree.node import DummyType
from . import type_names, TYPEDEF_DIR,TYPEDEF
from .base import TypeDir
import logging
logger = logging.getLogger(__name__)

class TypesValue(EtcXValue):
	"""An entry for storing a type"""
	ref = None

	async def has_update(self):
		await self._get_type()
		await super().has_update()

	async def init(self):
		await super().init()
		await self._get_type()

	async def _get_type(self, _=None):
		t = self.root.lookup(TYPEDEF_DIR)
		v = self._value
		mon = False
		while True:
			try:
				t = await t.lookup(v, name=TYPEDEF)
			except KeyError:
				try:
					v,_ = v.rsplit('/',1)
				except ValueError:
					raise KeyError(self.path+('.value',))
				else:
					mon = True
			else:
				break

		if mon:
			t.parent.add_monitor(self._get_type)
			# The idea is that if the type in question is ever added,
			# ref gets updated
		self.ref = t

class TypesDir(EtcDir):
	"""A subdirectory for storing types"""
	pass

TypesDir.register("*", cls=TypesDir)
TypesDir.register("*", cls=TypesValue)

TypeDir.register('types', cls=TypesDir, pri=5)
TypeDir.register('timestamp',cls=EtcFloat)
TypeDir.register('created',cls=EtcFloat)

class TypeNotFound(RuntimeError):
	pass

class DataDir(EtcDir):
	"""A subdirectory for storing values w/ directly-stored type"""
	type_dir = None  # e.g. "types"

	def _tagged_parent(self):
		p = self
		while p.name[0] != ':':
			p = p.parent
		return p
		
	def subtype(self,*path,dir=None,raw=False, **kw):
		if dir is not False or len(path) != 1:
			return super().subtype(*path,dir=dir,raw=raw,**kw)
#		if path == ('update_delay',):
#			import pdb;pdb.set_trace()
		p = self._tagged_parent()
		dpath = (self.type_dir,) + p.path[len(p.path)+1:] + path
		try:
			typ = p.lookup(dpath).ref.type.etcd_class
		except KeyError:
			logger.error("no type for %s",'/'.join(self.path+path),)
			typ = EtcValue
		if raw:
			typ = DummyType(typ, pri=2)
		return typ

class IndirectDataDir(DataDir):
	"""A subdirectory for storing values"""
	type_ref = None  # e.g. "typedef"
	type_root = None # e.g. TYPEDEF_DIR
	type_tag = None # e.g. TYPEDEF
	type_dir = None  # e.g. "types"

	def subtype(self,*path,dir=None,raw=False, **kw):
		if dir is not False or len(path) != 1:
			return super().subtype(*path,dir=dir,raw=raw,**kw)
		p = self._tagged_parent()
		dpath = (self.type_dir,) + p.path[len(p.path)+1:] + path
		refp = p[self.type_ref].ref
		try:
			typ = refp.lookup(dpath).ref.etcd_type
		except KeyError:
			logger.error("no type for %s",'/'.join(self.path+path),)
			typ = EtcValue
		if raw:
			typ = DummyType(typ, pri=2)
		return typ

