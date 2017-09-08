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
from etcd_tree import EtcRoot, EtcDir, EtcString, EtcInteger, EtcXValue, ReloadRecursive

import logging
logger = logging.getLogger(__name__)

from . import TYPEDEF_DIR,TYPEDEF

# This file contains all "singleton" etcd directories, i.e. those with
# fixed names at the root of the tree

class recEtcDir:
	"""an EtcDir mix-in which always loads its content up front"""
	@classmethod
	async def this_obj(cls, recursive, **kw):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_obj(recursive=recursive, **kw))

	async def init(self):
		self.force_updated()
		await super().init()

class MoatBusBase(EtcDir):
	"""\
		Base class for /bus/‹name› subsystems.
		"""
	pass

class MoatDeviceBase(EtcDir):
	"""\
		Base class for /device/‹name› subsystems.
		"""
	@property
	def task_monitor(self):
		return ()

class MoatRef(EtcXValue):
	"""An entry referencing some other node"""
	_ref = None

	@property
	def ref(self):
		if self._ref is not None:
			return self._ref
		self._ref = self.root.tree.lookup(self.value)
		return self._ref

class MoatLoader(EtcXValue):
	"""An entry referencing some code"""
	_code = None

	@property
	def code(self):
		if self._code is not None:
			return self._code
		if self.parent['language'] != 'python':
			raise RuntimeError("Wrong language for %s: %s" % ('/'.join(self.path), self.parent['language']))
		self._code = import_string(self.value)
		return self._code

class MoatLoaderDir(recEtcDir,EtcDir):
	"""Directory for /meta/module/‹subsys›"""
	pass
MoatLoaderDir.register('language', cls=EtcString)
MoatLoaderDir.register('descr', cls=EtcString)
MoatLoaderDir.register('summary', cls=EtcString)
MoatLoaderDir.register('*', cls=MoatLoader)

class MoatLoaded(EtcDir):
	"""\
		Directory for /‹subsys›/‹name›.
		Will lookup the class to use by way of /meta/modules."""

	@classmethod
	async def this_obj(cls, parent=None,recursive=None, pre=None, **kw):
		if recursive is None:
			raise ReloadData
		name = pre.key.rsplit('/',1)[1]
		m = (await parent.root.lookup('meta','module',name,parent.name)).code
		res = m(parent=parent,pre=pre,**kw)
		return res

	@property
	def task_monitor(self):
		return NoSubdirs(self)

class MoatLoadedDir(EtcDir):
	"""Directory for /‹subsys›"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return True
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
				changed = []
				for k,v in d.items():
					if k not in tt:
						logger.debug("%s: Add %s: %s", obj.prefix,k,v)
					else:
						ov = tt[k]
						ov = getattr(ov,'value',ov)
						if ov != v:
							logger.debug("%s: Update %s: %s => %s", obj.prefix,k,tt[k],v)
						else:
							continue
					changed.append((k,tt.get(k,'-'),v))
					r = await tt.set(k,v, sync=False)
				await tt.wait(r) # otherwise tt.keys() may change during execution
				for k in tt.keys():
					if k not in d:
						logger.debug("%s: Delete %s", obj.prefix,k)
						changed.append((k,tt[k],'-'))
						r = await tt.delete(k, sync=False)
				if changed:
					logger.info("%s: updated %s", obj.prefix, pformat(changed))
				else:
					logger.debug("%s: not changed", obj.prefix)
			else:
				logger.debug("%s: exists, skipped", obj.prefix)
		else:
			raise RuntimeError("%s: exists, language=%s" % (obj.prefix,lang))
		await tt.wait(r)

MoatMetaModule.register('*', cls=MoatLoaderDir)

class MoatMetaType(EtcDir):
	"""Singleton for /meta/type: type definitions"""
	async def init(self):
		from . import TYPEDEF
		from .base import TypeDir
		self.register('**',TYPEDEF, cls=TypeDir)
		await super().init()
		for v in self.values():
			await v.load(recursive=True)

class MoatMetaTask(EtcDir):
	"""Singleton for /meta/task: task definitions"""
	async def init(self):
		from moat.task import TASKDEF
		from moat.task.base import TaskDef

		self.register('*', cls=MoatMetaTask)
		self.register(TASKDEF, cls=TaskDef)
		await super().init()
	
	async def add_task(self, task, force=False):
		from moat.task import TASKDEF

		assert task.taskdef is not None, task
		d = dict(
			language='python',
			code=task.__module__+'.'+task.__name__,
			descr=task.summary,
		)
		doc=task.doc or task.__doc__
		if doc is not None:
			d['doc'] = doc
		if hasattr(task,'schema'):
			d['data'] = task.schema
		tt = await self.subdir(task.taskdef,name=TASKDEF, create=None)
		lang = tt.get('language',None)
		if lang is None:
			logger.info("%s: new", task.taskdef)
			await tt.update(d)
		elif lang == 'python':
			if force:
				changed = []
				for k,v in d.items():
					if k not in tt:
						logger.debug("%s: Add %s: %s", task.taskdef,k,v)
					elif tt[k] != v:
						logger.debug("%s: Update %s: %s => %s", task.taskdef,k,tt[k],v)
					else:
						continue
					changed.append((k,tt.get(k,'-'),v))
					await tt.set(k,v)
				for k in tt.keys():
					if k not in d:
						logger.debug("%s: Delete %s", task.taskdef,k)
						r = await tt.delete(k, sync=False)
						changed.append((k,tt[k],'-'))

				if changed:
					logger.info("%s: updated: %s", task.taskdef, pformat(changed))
				else:
					logger.debug("%s: not changed", task.taskdef)
			else:
				logger.debug("%s: exists, skipped", task.taskdef)
		else:
			raise RuntimeError("%s: exists, language=%s" % (task.taskdef,lang))

class MoatMetaWeb(recEtcDir,EtcDir):
	"""Hierarchy for /meta/web: HTML front-end definitions"""
	_reg_done = False
	@classmethod
	async def this_obj(cls, recursive, **kw):
		if not cls._reg_done:
			cls._reg_done = True
			from moat.web import WEBDEF
			from moat.web.base import WebdefDir

			cls.register('*', cls=MoatMetaWeb)
			cls.register(WEBDEF, cls=WebdefDir)
		return (await super().this_obj(recursive, **kw))
	
	async def add_webdef(self, webdef, force=False):
		from moat.web import WEBDEF

		assert webdef.name is not None, webdef
		d = dict(
			code=webdef.__module__+'.'+webdef.__name__,
			descr=webdef.summary,
			doc=webdef.doc or webdef.__doc__,
		)
		if hasattr(webdef,'schema'):
			d['data'] = webdef.schema
		tt = await self.subdir(webdef.name,name=WEBDEF, create=None)
		if force:
			changed = []
			for k,v in d.items():
				if k not in tt:
					logger.debug("%s: Add %s: %s", webdef.name,k,v)
				elif tt[k] != v:
					logger.debug("%s: Update %s: %s => %s", webdef.name,k,tt[k],v)
				else:
					continue
				changed.append((k,tt.get(k,'-'),v))
				await tt.set(k,v)
			for k in tt.keys():
				if k not in d:
					logger.debug("%s: Delete %s", webdef.name,k)
					r = await tt.delete(k, sync=False)
					changed.append((k,tt[k],'-'))

			if changed:
				logger.info("%s: updated: %s", webdef.name, pformat(changed))
			else:
				logger.debug("%s: not changed", webdef.name)
		else:
			logger.debug("%s: exists, skipped", webdef.name)

class MoatMeta(EtcDir):
	"""Singleton for /meta"""
	async def init(self):
		self.register('type', cls=MoatMetaType)
		self.register('task', cls=MoatMetaTask)
		self.register('web', cls=MoatMetaWeb)
		self.register('module', cls=MoatMetaModule)
		await super().init()
		try:
			await self['type']
		except KeyError:
			pass # not yet present

class MoatConfig(recEtcDir,EtcDir):
	"""Singleton for /config"""
	pass
	# only here to preload the whole thing

class MoatInfraSub(EtcDir):
	pass

class MoatInfra(EtcDir):
	async def init(self):
		from moat.infra.base import InfraHost, InfraStatic
		self.register("*", cls=MoatInfraSub)
		self.register(":static", cls=InfraStatic)

		MoatInfraSub.register("*", cls=MoatInfraSub)
		MoatInfraSub.register(":host", cls=InfraHost)

	async def host(self, host, **kw):
		"""Lookup a host by its DNS name."""
		from moat.infra import INFRA
		return (await self.subdir(host.split('.')[::-1], name=INFRA, **kw))

class MoatStatusRun(EtcDir):
	"""Singleton for /status/run"""
	async def init(self):
		from moat.task import TASKSTATE
		from moat.task.base import TaskState
		self.register('**',TASKSTATE, cls=TaskState)
		await super().init()
	
class MoatStatusErr(EtcDir):
	"""Singleton for /status/error"""
	async def init(self):
		from .error import ErrorRecord
		self.register('*', '*', cls=ErrorRecord)
		await super().init()
	
class MoatWeb(EtcDir):
	"""Singleton for /web"""
	async def init(self):
		from moat.web import WEBDATA_DIR,WEBSERVER_DIR,WEBCONFIG
		from moat.web.base import WebdataBase, WebserverBase, WebconfigDir
		self.register(*WEBDATA_DIR[1:], cls=WebdataBase)
		self.register(*WEBSERVER_DIR[1:], cls=WebserverBase)
		self.register(WEBCONFIG, cls=WebconfigDir)
		await super().init()

	@property
	def task_monitor(self):
		return StaticSubdirs(self)
	def task_for_subdir(self,d):
		from moat.web import WEBSERVER_DIR
		if d == WEBSERVER_DIR[1]:
			return True
	
class MoatStatus(EtcDir):
	"""Singleton for /status"""
	async def init(self):
		self.register('run', cls=MoatStatusRun)
		self.register('error', cls=MoatStatusErr)
		await super().init()

class MoatTask(EtcDir):
	"""/task and 'plain' dirs below that"""
	async def init(self):
		from moat.task import TASK
		from moat.task.base import TaskDir
		self.register(TASK, cls=TaskDir)
		self.register('*', cls=MoatTask)
		await super().init()

	async def add_task(self, path, taskdef, force=False, parent=None, **kw):
		from moat.task import TASK,TASKDEF_DIR,TASKDEF

		if isinstance(path,str):
			p = path
			path = tuple(path.split('/'))
		else:
			p = '/'.join(path)

		if isinstance(taskdef,str):
			tds = taskdef
			taskdef = tuple(taskdef.split('/'))
		else:
			tds = '/'.join(taskdef)

		td = await self.root.subdir(*(TASKDEF_DIR+taskdef),name=TASKDEF)
		logger.debug('Taskdef %s for %s is %s', tds,path,td.get('language','?'))
		r = None

		# .taskdef is not in there because it needs to be set last
		d = dict(
			data=kw,
		)
		if parent is not None:
			d['parent'] = '/'.join(parent.path)
		tt = await self.subdir(*path,name=TASK, create=None)
		if force or 'taskdef' not in tt:
			is_new = ('taskdef' not in tt)
			changed = []

			# Setting taskdef must be first, as the node's data type is
			# determined from that
			if tt.get('taskdef','') != tds:
				await tt.set('taskdef',tds)
				tt.force_updated() # required for getting the schema

			for k,v in d.items():
				if k not in tt:
					logger.debug("%s: Add %s: %s", p,k,v)
				elif tt[k] != v:
					logger.debug("%s: Update %s: %s => %s", p,k,tt[k],v)
				else:
					continue
				changed.append((k,tt.get(k,'-'),v))
				r = await tt.set(k,v, sync=False)
			for k in list(tt.keys()): # may change size during "await" in the loop
				if k == "taskdef":
					pass
				elif k not in d:
					logger.debug("%s: Delete %s", p,k)
					changed.append((k,tt[k],'-'))
					r = await tt.delete(k, sync=False)

			if is_new:
				logger.info("%s: created", p)
			elif changed:
				logger.info("%s: updated: %s", p, pformat(changed))
			else:
				logger.debug("%s: not changed", p)
		else:
			logger.debug("%s: exists, skipped", p)
		if r is not None:
			await self.root.wait(r)

class _Subdirs(object):
	"""Common base class for task-specific subdirectory monitoring"""

	# This works by first iterating the child nodes. When they have been
	# exhausted, poll() waits for additional add or drop events.
	# 
	# _add and _del are common code to build the events which the iterator
	# returns. They filter duplicates.

	def __init__(self,dir):
		self.dir = dir
		self.known = set()
	async def __aiter__(self):
		self.it = iter(list(self.dir.keys()))
		return self

	def _add(self,a):
		if a not in self.known:
			if self.dir.task_for_subdir(a):
				self.known.add(a)
				return "scan",self.dir.path+(a,),{}

	def _del(self,a):
		if a in self.known:
			self.known.remove(a)
			return "drop",self.dir.path+(a,)

	async def __anext__(self):
		while self.it is not None:
			try:
				res = next(self.it)
			except StopIteration:
				self.it = None
				return ("watch",)
			else:
				res = self._add(res)
				if res is not None:
					return res
		return (await self.poll())

	async def poll(self):
		raise RuntimeError("You need to override %s.poll"%(self.__class__.__name__,))

class NoSubdirs(object):
	"""fake async iterator that doesn't return anything"""
	def __init__(self,dir):
		pass
	async def __aiter__(self):
		return self
	async def __anext__(self):
		raise StopAsyncIteration
	
class Subdirs(_Subdirs):
	"""async iterator for monitoring a dynamic subdirectory"""

	# Here, poll() returns events from a queue that's fed by a monitor
	# procedure added to the directory we're interested in.

	async def __aiter__(self):
		await super().__aiter__()
		self.q = asyncio.Queue(loop=self.dir._loop)
		logger.debug("CHG MON %s",self.dir)
		self.mon = self.dir.add_monitor(self._mon)
		return self

	async def poll(self):
		"""Read the event queue"""
		while True:
			res = await self.q.get()
			if res is None:
				raise StopAsyncIteration
			t,a = res
			logger.debug("CHG %s: %s %s",self.dir,t,a)
			if t == '+':
				res = self._add(a)
			elif t == '-':
				res = self._del(a)
			else:
				assert False,(t,a)
			if res is not None:
				return res

	def _mon(self,x):
		"""Watch a directory for changes"""
		assert x is self.dir
		if x._seq is None:
			self.q.put_nowait(None)
			return
		for a in x.added:
			self.q.put_nowait(('+',a))
		for a in x.deleted:
			self.q.put_nowait(('-',a))

class StaticSubdirs(_Subdirs):
	"""async iterator for monitoring a static subdirectory"""

	# This subdir doesn't expect any changes, so no monitor.

	async def poll(self):
		raise StopAsyncIteration

class MoatRoot(EtcRoot):
	"""Singleton for etcd / (root)"""
	async def init(self):
		self._managed = WeakValueDictionary()

		self.register('meta', cls=MoatMeta)
		self.register('web', cls=MoatWeb)
		self.register('task', cls=MoatTask)
		self.register('status', cls=MoatStatus)
		self.register('device', cls=MoatLoadedDir)
		self.register('bus', cls=MoatLoadedDir)
		self.register('config', cls=MoatConfig)
		self.register('infra', cls=MoatInfra)
		await super().init()
		# preload these sub-trees
		await self['config']
		try:
			await self['meta']
		except KeyError: # does not exist yet
			pass

	def type(self,p):
		return self.lookup(*(TYPEDEF_DIR+p.split('/')),name=TYPEDEF)

	@property
	def task_monitor(self):
		return StaticSubdirs(self)
	def task_for_subdir(self,d):
		if d in ("bus","device","web"):
			return True

	def managed(self,dev):
		### XXX ???
		pass

import yaml
def _REFwrapper(dumper,data):
	return dumper.represent_scalar('!MoatRef', data.value)
yaml.add_representer(MoatRef,_REFwrapper)

