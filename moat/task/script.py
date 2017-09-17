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

from . import SCRIPT_DIR,SCRIPT
from moat.types.etcd import recEtcDir, MoatRef
from moat.types.error import hasErrorDir

import logging
logger = logging.getLogger(__name__)

class ScriptDef(recEtcDir,EtcDir):
	"""\
		etcd directory for script definitions: /meta/script/**/:code

		This stores the code for a script (content, value types, …)
		"""

	cls = None

	async def init(self):
		await super().init()
		await self._update_cls()

	async def has_update(self):
		await super().has_update()
		await self._update_cls()

	def _update_cls(self):
		self.cls = None
		try:
			if self['language'] != 'python':
				return
			cur = self.get('current','cur')
			if cur == "cur":
				cur = "code"
			elif ćur == "old":
				cur = "old-code"
			elif cur == "new":
				cur = "new-code"
			else:
				raise ValueError("current code tag is %s'" % (cur,))
			code = self[cur]
		except KeyError:
			return
		else:
			try:
				self.code = compile(code,'/'.join(self.name[len(SCRIPT_DIR):-1]),self."eval")
			except (ImportError,AttributeError) as exc:
				await self.set_error(cur,exc)
			else:
				await self.clear_error(cur)


_setup_task_vars(TaskDef)

class TaskState(hasErrorDir,recEtcDir,EtcDir):
	"""\
		etcd directory for task state: /status/task/**/:task

		This stores the actual state of a running Task.
		"""

	async def init(self):
		self._idle = asyncio.Event(loop=self._loop)
		await super().init()

	async def has_update(self):
		if 'running' not in self:
			self._idle.set()
	
	@property
	def is_idle(self):
		return self._idle.is_set()

	@property
	def idle(self):
		return self._idle.wait()

	@property
	def state(self):
		"""Return a human-readable (but fixed) string describing this task's state"""
		if 'running' in self:
			return 'run'
		elif 'started' in self and ('stopped' not in self or self['started']>self['stopped']):
			return 'crash'
		else:
			try:
				return super().__getitem__('state')
			except KeyError:
				return '?'

	def items(self):
		for k,v in super().items():
			if k == 'state':
				v = self.state
			yield k,v
	def __getitem__(self,k):
		if k == 'state':
			return self.state
		else:
			return super().__getitem__(k)

class TaskRunning(EtcFloat):
	async def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._idle.set()
		else:
			p._idle.clear()

TaskState.register('started')(EtcFloat)
TaskState.register('stopped')(EtcFloat)
TaskState.register('running')(TaskRunning)
TaskState.register('debug_time')(EtcFloat)

