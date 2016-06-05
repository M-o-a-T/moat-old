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

from etcd_tree import EtcFloat,EtcString, ReloadRecursive
from dabroker.util import import_string

from . import TASK_DIR,TASKSCAN_DIR
from moat.script.task import Task

import logging
logger = logging.getLogger(__name__)


class Collector(Task):
	"""\
		This task runs a task collector.

		Collectors are attached to etcd nodes by way of a 'task_monitor' 
		attribute/property which supports the async iteration protocol.
		The node is found by simply chopping %s off the front
		of this task's path.
		""" % ('/'.join(TASKSCAN_DIR),)

	taskdef="task/collect"
	summary="A Task which runs a task collector"
	schema = {}

	async def task(self):
		root = await self.cmd.root._get_tree()
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
			logger.debug("Collecting %s: %s",self.path,r)
			if self.cmd.root.verbose > 2:
				print(r)
			typ = r[0]
			if typ == "add":
				typ,taskdef,path,kw = r
				await tasks.add_task(path=path, taskdef=taskdef, parent=self.taskdir, **kw)
				if len(path) == len(master.path)+1 and path[:-1] == master.path:
					known.add(path[-1])
			elif typ == "scan":
				typ,path,kw = r
				await scantasks.add_task(path=path, taskdef=self.taskdef, parent=self.taskdir, **kw)
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

