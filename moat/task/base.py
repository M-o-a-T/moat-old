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
from etcd_tree import EtcFloat,EtcString,EtcDir, ReloadRecursive
from etcd_tree.node import DummyType
from qbroker.util import import_string

from . import _VARS, TASKDEF_DIR,TASKDEF,TASKDEF_DEFAULT, SCRIPT_DIR,SCRIPT
from moat.script.data import TaskScriptDataDir
from moat.types import TYPEDEF,TYPEDEF_DIR
from moat.task import TASK_REF,TASK_TYPE,TASK_DATA, SCRIPT_REF,SCRIPT_DATA
from moat.types.etcd import recEtcDir, MoatRef
from moat.types.data import DataDir,TypesDir,IndirectDataDir
from moat.types.error import hasErrorDir
from moat.util import OverlayDict

import logging
logger = logging.getLogger(__name__)

def _setup_task_vars(types):
	"""Tasks have several global config variables. Their types are set here.
		This is called with the class/typepath to register:
		TASK_DIR/**/TASK or TASKDEF_DIR/**/TASKDEF
		"""
	from etcd_tree.etcd import EtcTypes
	from etcd_tree.node import EtcFloat,EtcInteger,EtcBoolean
	for t in _VARS:
		if t == "ttl":
			types.register(t, cls=EtcInteger)
		elif t == "one-shot":
			types.register(t, cls=EtcBoolean)
		else:
			types.register(t, cls=EtcFloat)

class TaskdefName(MoatRef.at(TASKDEF_DIR,TASKDEF)):
	async def has_update(self):
		await super().has_update()
		p = self.parent
		if p is not None:
			p.taskdef_pending.clear()
			self.root.task(p._update_taskdef,self._value)

	async def init(self):
		await super().init()
		await self.parent._update_taskdef(self._value)

class TaskDir(recEtcDir,EtcDir):
	"""\
		etcd directory for tasks: /task/**/:task

		This stores the data for one instantiation of a Task.
		"""
	
	taskdef = None
	taskdef_name = ''
	taskdef_pending = None

	# the actual task, if running
	# managed by moat.script.task.TaskMaster
	# IMPORTANT: only to be used for debugging and testing!
	_task = None

	def __init__(self, *a,**k):
		super().__init__(*a,**k)
		self.taskdef_pending = asyncio.Event(loop=self._loop)

	async def init(self):
		if 'scipt' in self:
			self.script_data = OverlayDict(self[SCRIPT_DATA],self[SCRIPT_REF].ref[SCRIPT_DATA])
		self.data = OverlayDict(self[TASK_DATA],
		              OverlayDict(self[TASK_REF].ref[TASK_DATA],
					              self.root.lookup(TASKDEF_DIR,name=TASKDEF_DEFAULT)[TASK_DATA]))
		await super().init()

	@property
	def cls(self):
		return self.taskdef.cls

	@property
	def ready(self):
		return asyncio.gather(super().ready,self.taskdef.ready, loop=self._loop)

	@property
	async def taskdef_ready(self):
		redo = True
		while redo:
			redo = False
			try:
				td = self.get('taskdef', raw=True)
			except KeyError:
				assert not self.taskdef_pending.is_set()
				redo = True
			else:
				if not td.is_ready:
					await td.ready
					redo = True
			if self.taskdef_pending is None:
				redo = True
			elif not self.taskdef_pending.is_set():
				await self.taskdef_pending.wait()
				redo = True
			if not self.taskdef.is_ready:
				await self.taskdef.ready
				redo = True

	@property
	def is_ready(self):
		return super().is_ready and self.taskdef.is_ready

	async def _update_taskdef(self,name=None):
		if name != self.taskdef_name:
			if TASK_DATA in self:
				self[TASK_DATA].throw_away()
			td_path = tuple(x for x in name.split('/') if x != "")
			self.taskdef = await self.root.subdir(TASKDEF_DIR+td_path+(TASKDEF,), create=False)
			self.taskdef_name = name
			if TASK_DATA in self:
				await self[TASK_DATA]
		self.taskdef_pending.set()

	async def _fill_data(self,pre,recursive):
		if not recursive:
			raise ReloadRecursive
		for c in pre.child_nodes:
			if c.name == 'taskdef':
				await self._update_taskdef(c.value)
				break
		await super()._fill_data(pre,recursive)

class TaskdefDataDir(DataDir):
	"""\
        Directory for /meta/task/…/:taskdef/data/**
        """
	type_dir = "types"
class TaskDataDir(IndirectDataDir):
	"""\
        Directory for entries in /task/…/:task/data/**
        """
	type_ref = "taskdef"
	type_root = TASKDEF_DIR
	type_tag = TASKDEF
	type_dir = "types"

_setup_task_vars(TaskDir)
TaskDir.register('parent', cls=MoatRef)
TaskDir.register(TASK_REF, cls=TaskdefName, pri=8)
TaskDir.register(TASK_DATA, cls=TaskDataDir)
TaskDir.register(SCRIPT_DATA, cls=TaskScriptDataDir) ## for scripts

class TaskDef(recEtcDir,EtcDir):
	"""\
		etcd directory for task definitions: /meta/task/**/:taskdef

		This stores generic parameters for a Task (name, filepath/class/code, …).
		"""

	cls = None

	async def init(self):
		await super().init()
		self._update_cls()

	async def has_update(self):
		await super().has_update()
		self._update_cls()

	def _update_cls(self):
		self.cls = None
		try:
			if self['language'] != 'python':
				return
			code = self['code']
		except KeyError:
			return
		else:
			try:
				self.cls = import_string(code)
			except (ImportError,AttributeError):
				logger.error("%s: Unable to import %s", '/'.join(self.path[:-1]),self['code'])

_setup_task_vars(TaskDef)
TaskDef.register(TASK_TYPE, cls=TypesDir,pri=8)
TaskDef.register(TASK_DATA, cls=TaskdefDataDir,pri=5)

