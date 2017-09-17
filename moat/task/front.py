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
from etcd_tree import EtcFloat,EtcString, ReloadRecursive

from . import SCRIPT_DIR,SCRIPT, TASK_DIR,TASK
from moat.script.task import Task

import logging
logger = logging.getLogger(__name__)

class MoatScript(object):
	"""\
		The class which controls interactions of a user scriopt with the
		rest of MoaT.
		"""
	
	def __init__(self, reg):
		self.reg = reg
	
	@property
	def root(self):
		return self.reg.root

class Scriptor(Task):
	"""\
		This task runs a script.

		Scripts are stored in etcd at /meta/script/…/:code/code.
		The '…' part is stored in the task's "script" attribute.
		""" % ('/'.join(TASKSCAN_DIR),)

	taskdef="task/script"
	summary="A Task which runs a user-defined script"
	schema = {}

	async def task(self):
		root = await self.cmd.root._get_tree()
		script = self['script']

		reg = Reg(self)
		moat = MoatScript(reg)

		master = (await root.lookup(*self.path[len(TASKSCAN_DIR)-len(TASK_DIR):]))
		coll = master.task_monitor
		tasks = await root.subdir(*TASK_DIR)
		scantasks = await root.subdir(*TASKSCAN_DIR)
		me = self.taskdir.parent
		logger.debug("Start collecting: %s",self.path)

		# The results may include stuff that is not below "our" path.
		# But if it is, remember
		known = set()

		async def found(r):
			logger.debug("Collect %s: %s",self.name,r)
#			if self.cmd.root.verbose > 2:
#				print(r)
			typ = r[0]
			if typ == "add":
				typ,taskdef,path,kw = r
				kw.setdefault('parent',master)
				await tasks.add_task(path=path, taskdef=taskdef, **kw)
				if len(path) == len(master.path)+1 and path[:-1] == master.path:
					known.add(path[-1])
			elif typ == "scan":
				typ,path,kw = r
				kw.setdefault('parent',master)
				await scantasks.add_task(path=path, taskdef=self.taskdef, **kw)
				if len(path) == len(master.path)+1 and path[:-1] == master.path:
					known.add(path[-1])
			elif typ == "drop":
				typ,path = r
				t = await tasks.subdir(*path)
				await t.delete(recursive=True)
				if len(path) == len(master.path)+1 and path[:-1] == master.path:
					try:
						known.remove(path[-1])
					except KeyError:
						pass
			elif typ == "watch":
				for k in list(me.keys()):
					if k[0] != ':' and k not in known:
						logger.info("Deleting "+'/'.join(me.path+(k,)))
						await me.delete(k)
				if self.cfg.get('one-shot',False):
					raise StopAsyncIteration
			else:
				raise NotImplementedError("Unknown Collect result: "+repr(r))

		try:
			if hasattr(coll,'__aiter__'):
				async for r in coll:
					await found(r)
			else:
				for r in coll:
					await found(r)
		except StopAsyncIteration:
			pass

		# sleep
		if not self.cfg.get('one-shot',False):
			while True:
				await asyncio.sleep(999999,loop=self.loop)

