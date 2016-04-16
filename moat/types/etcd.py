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

# This file contains all "singleton" etcd directories, i.e. those with
# fixed names at the root of the tree

class recEtcDir(EtcDir):
	"""an EtcDir which always loads its content up front"""
	@classmethod
	async def this_class(cls, pre,recursive):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_class(pre=pre,recursive=recursive))

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
	@property
	def code(self):
		if self.parent['language'] != 'python':
			raise RuntimeError("Wrong language for %s: %s" % ('/'.join(self.path), self.parent['language']))
		return import_string(self.value)

class MoatLoaderDir(recEtcDir):
	"""Directory for /meta/module/‹subsys›"""
	pass
MoatLoaderDir.register('language', cls=EtcString)
MoatLoaderDir.register('*', cls=MoatLoader)

class MoatLoaded(EtcDir):
	"""\
		Directory for /‹subsys›/‹name›.
		Will lookup the class to use by way of /meta/modules."""
	@classmethod
	async def _new(cls,pre,parent,**kw):
		import pdb;pdb.set_trace()
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
MoatMetaModule.register('*', cls=MoatLoaderDir)

class MoatMetaType(EtcDir):
	"""Singleton for /meta/type"""
	async def init(self):
		from . import TYPEDEF
		from .base import TypeDir
		self.register('**',TYPEDEF, cls=TypeDir)
		await super().init()

class MoatMetaTask(EtcDir):
	"""Singleton for /meta/task"""
	async def init(self):
		from moat.task import TASKDEF
		from moat.task.base import TaskDef
		self.register('**',TASKDEF, cls=TaskDef)
		await super().init()

class MoatMeta(EtcDir):
	"""Singleton for /meta"""
	async def init(self):
		self.register('type', cls=MoatMetaType)
		self.register('task', cls=MoatMetaTask)
		await super().init()
		await self['type']

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
		await self['meta']

	def managed(self,dev):
		### XXX ???
		pass
