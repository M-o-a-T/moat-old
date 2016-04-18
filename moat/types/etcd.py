# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

from etcd_tree import EtcRoot, EtcDir, EtcString, ReloadRecursive
from weakref import WeakValueDictionary
from dabroker.util import import_string

import logging
logger = logging.getLogger(__name__)

# This file contains all "singleton" etcd directories, i.e. those with
# fixed names at the root of the tree

class recEtcDir(EtcDir):
	"""an EtcDir which always loads its content up front"""
	@classmethod
	async def this_obj(cls, recursive, **kw):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_obj(recursive=recursive, **kw))

class MoatDeviceBase(EtcDir):
	"""\
		Base class for /bus/‹name› subsystems.
		"""
	pass

class MoatBusBase(EtcDir):
	"""\
		Base class for /bus/‹name› subsystems.
		"""
	pass

class MoatLoader(EtcString):
	"""Directory for /meta/module/‹subsys›/‹name›"""
	_code = None

	@property
	def code(self):
		if self._code is not None:
			return self._code
		if self.parent['language'] != 'python':
			raise RuntimeError("Wrong language for %s: %s" % ('/'.join(self.path), self.parent['language']))
		self._code = import_string(self.value)
		return self._code

class MoatLoaderDir(recEtcDir):
	"""Directory for /meta/module/‹subsys›"""
	pass
MoatLoaderDir.register('language', cls=EtcString)
MoatLoaderDir.register('description', cls=EtcString)
MoatLoaderDir.register('summary', cls=EtcString)
MoatLoaderDir.register('*', cls=MoatLoader)

class MoatLoaded(EtcDir):
	"""\
		Directory for /‹subsys›/‹name›.
		Will lookup the class to use by way of /meta/modules."""
	@classmethod
	async def _new(cls,pre,parent,**kw):
		m = parent.root.lookup('meta','module',pre.key[-1],parent.name).code
		res = await m._new(pre=pre,parent=parent,**kw)
		return res

class MoatLoadedDir(EtcDir):
	"""Directory for /‹subsys›"""
	pass
MoatLoadedDir.register('*', cls=MoatLoaded)

class MoatMetaModule(EtcDir):
	"""Singleton for /meta/module"""
	async def init(self):
		self.register('*', cls=MoatLoaderDir)
		await super().init()
	
	async def names_for(self, name):
		"""\
			Return all object names with a certain key.

			This is useful for enumerating module names that implement a
			feature, but without loading the code yet.
			"""
		res = []
		for v in self.values():
			v = await v
			if name in v:
				res.append(v)
		return res

	async def add_module(self, obj, force=False):
		d = dict(
			language='python',
			descr=obj.summary,
			doc=(getattr(obj,'doc',None) or obj.__doc__),
			code=obj.__module__+'.'+obj.__name__,
		)
		for k,v in obj.entries():
			d[k] = v
		if hasattr(obj,'schema'):
			d['data'] = obj.schema
		tt = await self.subdir(obj.prefix, create=None)
		r = None
		lang = tt.get('language',None)
		if lang is None:
			logger.info("%s: new", obj.prefix)
			await tt.update(d, _sync=False)
		elif lang == 'python':
			if force: 
				changed = False
				for k,v in d.items():
					if k not in tt:
						logger.debug("%s: Add %s: %s", obj.prefix,k,v)
					elif tt[k] != v:
						logger.debug("%s: Update %s: %s => %s", obj.prefix,k,tt[k],v)
					else:
						continue
					r = await tt.set(k,v, sync=False)
					changed = True
				for k in tt.keys():
					if k not in d:
						r = await tt.delete(k, sync=False)
						logger.debug("%s: Delete %s", obj.prefix,k)
						changed = True
				if changed:
					logger.info("%s: updated", obj.prefix)
				else:
					logger.debug("%s: not changed", obj.prefix)
			else:
				logger.debug("%s: exists, skipped", obj.prefix)
		else:
			raise RuntimeError("%s: exists, language=%s" % (obj.prefix,lang))
		await tt.wait(r)

MoatMetaModule.register('*', cls=MoatLoaderDir)

class MoatMetaType(EtcDir):
	"""Singleton for /meta/type"""
	async def init(self):
		from . import TYPEDEF
		from .base import TypeDir
		self.register('**',TYPEDEF, cls=TypeDir)
		await super().init()
		for v in self.values():
			await v.load(recursive=True)

class MoatMetaTask(EtcDir):
	"""Singleton for /meta/task"""
	async def init(self):
		from moat.task import TASKDEF
		from moat.task.base import TaskDef

		self.register('**',TASKDEF, cls=TaskDef)
		await super().init()
	
	async def add_task(self, task, force=False):
		from moat.task import TASKDEF

		assert task.name is not None
		d = dict(
			language='python',
			code=task.__module__+'.'+task.__name__,
			descr=task.summary,
			doc=task.doc or task.__doc__,
		)
		if hasattr(task,'schema'):
			d['data'] = task.schema
		tt = await self.subdir(task.name,name=TASKDEF, create=None)
		lang = tt.get('language',None)
		if lang is None:
			logger.info("%s: new", task.name)
			await tt.update(d)
		elif lang == 'python':
			if force:
				changed = False
				for k,v in d.items():
					if k not in tt:
						logger.debug("%s: Add %s: %s", task.name,k,v)
					elif tt[k] != v:
						logger.debug("%s: Update %s: %s => %s", task.name,k,tt[k],v)
					else:
						continue
					await tt.set(k,v)
					changed = True
				for k in tt.keys():
					if k not in d:
						logger.debug("%s: Delete %s", task.name,k)
						r = await tt.delete(k, sync=False)
						changed = True

				if changed:
					logger.info("%s: updated", task.name)
				else:
					logger.debug("%s: not changed", task.name)
			else:
				logger.debug("%s: exists, skipped", task.name)
		else:
			raise RuntimeError("%s: exists, language=%s" % (task.name,lang))


class MoatMeta(EtcDir):
	"""Singleton for /meta"""
	async def init(self):
		self.register('type', cls=MoatMetaType)
		self.register('task', cls=MoatMetaTask)
		self.register('module', cls=MoatMetaModule)
		await super().init()
		try:
			await self['type']
		except KeyError:
			pass # not yet present

class MoatConfig(recEtcDir):
	"""Singleton for /config"""
	pass
	# only here to preload the whole thing

class MoatStatusRun(EtcDir):
	"""Singleton for /status/run"""
	async def init(self):
		from moat.task import TASKSTATE
		from moat.task.base import TaskState
		self.register('**',TASKSTATE, cls=TaskState)
		await super().init()
	
class MoatStatus(EtcDir):
	"""Singleton for /status"""
	async def init(self):
		self.register('run', cls=MoatStatusRun)
		await super().init()

class MoatTask(EtcDir):
	"""Singleton for /task"""
	async def init(self):
		from moat.task import TASK
		from moat.task.base import Task
		self.register('**',TASK, cls=Task)
		await super().init()

class MoatRoot(EtcRoot):
	"""Singleton for etcd / (root)"""
	async def init(self):
		self._managed = WeakValueDictionary()

		self.register('meta', cls=MoatMeta)
		self.register('task', cls=MoatTask)
		self.register('status', cls=MoatStatus)
		self.register('device', cls=MoatLoadedDir)
		self.register('bus', cls=MoatLoadedDir)
		self.register('config', cls=MoatConfig)
		await super().init()
		# preload these sub-trees
		await self['config']
		try:
			await self['meta']
		except KeyError: # does not exist yet
			pass

	def managed(self,dev):
		### XXX ???
		pass
