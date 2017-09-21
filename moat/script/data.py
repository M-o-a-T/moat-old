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

from moat.task import SCRIPT_DIR,SCRIPT, TASK_DIR,TASK
from moat.script.task import Task
from moat.types.data import TypesDir,TypesValue, DataDir,IndirectDataDir
from moat.types.etcd import recEtcDir

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

	async def _update_cls(self):
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
				self.code = compile(code,'/'.join(self.name[len(SCRIPT_DIR):-1]),self,"expr")
			except (ImportError,AttributeError) as exc:
				await self.set_error(cur,exc)
			else:
				await self.clear_error(cur)

class ScriptTypesDir(TypesDir):
	pass
class ScriptTypesValue(TypesValue):
	pass
ScriptDef.register("types", cls=ScriptTypesDir, pri=5)
ScriptTypesDir.register("*", cls=ScriptTypesDir)
ScriptTypesDir.register("*", cls=ScriptTypesValue)


class ScriptDataDir(DataDir):
	"""\
		Directory for /meta/script/…/:code/values/**
		"""
	type_dir = "types"

ScriptDataDir.register('*', cls=ScriptDataDir)

class TaskScriptDataDir(IndirectDataDir):
	"""\
		Directory for entries in /task/…/:task/values/**
		"""
	type_ref = "script"
	type_root = SCRIPT_DIR
	type_tag = SCRIPT
	type_dir = "types"

TaskScriptDataDir.register('*', cls=TaskScriptDataDir)

ScriptDef.register("values", cls=ScriptDataDir, pri=3)

