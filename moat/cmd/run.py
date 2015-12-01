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

"""List of known Tasks"""

import asyncio
import os

from ..script import Command, CommandError
from ..script.task import TaskMaster
from ..task import TASK_DIR,TASK
from etctree.util import from_etcd
from etctree.node import mtDir
from functools import partial
import aioetcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['RunCommand']

class RunCommand(Command):
	name = "run"
	summary = "Start tasks"""
	description = """\
Run MoaT tasks.

by default, start every task that's defined for this host.

"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
            action="count", dest="this", default=0,
            help="Run this job only (add -t for sub-paths)")
		self.parser.add_option('-l','--list',
            action="store_true", dest="list",
            help="List jobs' state instead of running them")
		self.parser.add_option('-x','--noref',
            action="store_true", dest="noref",
            help="Do not follow :ref entries")
		self.parser.add_option('-g','--global',
            action="store_true", dest="is_global",
            help="Do not prepend the appname to the paths")
		self.parser.add_option('-s','--standalone',
            action="store_true", dest="standalone",
            help="Do not update jobs when the etcd list changes")
		self.parser.add_option('-k','--kill-fail',
            action="store_true", dest="killfail",
            help="Exit when a job fails; no restart or whatever")

	async def do_async(self,args):
		opts = self.options
		if opts.is_global and not args and not opts.list:
			raise CommandError("You can't run the whole world.")

		etc = await self.root._get_etcd()
		if args:
			if not opts.is_global:
				args = [self.root.app+'/'+t for t in args]
			args = [TASK_DIR+'/'+t for t in args]
		elif opts.is_global:
			args = [TASK_DIR]
		else:
			args = [TASK_DIR+'/'+self.root.app]
		
		paths = []
		for t in args:
			paths.append(await etc.tree(t))
		depth = opts.this
		tasks = []
		while paths and depth != 1:
			depth -= 1
			n_p = []
			for t in paths:
				for k,v in t.items():
					if k == TASK:
						if depth < 2:
							tasks.append(v)
					elif k.startswith(':'):
						continue
					elif isinstance(v,mtDir):
						n_p.append(v)
				paths = n_p
		if opts.list:
			for task in sorted(tasks, key=lambda _:_.path):
				path = task.path[len(TASK_DIR)+1:-(len(TASK)+1)]
				print(path,task.get('name','-'),task.get('descr','-'), sep='\t')
			return

		def _report(path, state, value=None):
			if self.root.verbose:
				if value is None:
					value = ()
				else:
					value = (value,)
				print(path,state, *value, sep='\t', file=self.stdout)

		js = {}
		for task in tasks:
			path = task.path[len(TASK_DIR)+1:-(len(TASK)+1)]
			try:
			    j = TaskMaster(self, path, callback=partial(_report, path))
			except Exception as exc:
				logger.exception("Could not set up %s (%s)",t.path,t.get('name',path))
				if opts.killfail:
					return 2
			else:
				js[j.path] = (t,j)
		jobs = {}
		for name,tj in js.items():
			t,j = tj
			try:
				await j.init()
			except Exception as exc:
				logger.exception("Could not init %s (%s)",t.path,t.get('name',path))
				if opts.killfail:
					for j in jobs.values():
						j.cancel()
					return 2
			else:
				jobs[j.name] = j
		del js
		try:
			while jobs:
				done,pending = await asyncio.wait(jobs.values(), loop=self.root.loop, return_when=asyncio.FIRST_COMPLETED)
				for j in done:
					del jobs[j.name]
					try:
						r = j.result()
					except Exception as exc:
						log_exception("Running %s",j.name)
						if opts.killfail:
							break
					else:
						if self.root.verbose > 1:
							print(j.name,r, sep='\t', file=self.stdout)

		finally:
			for j in jobs.values():
				try:
					await j.cancel()
				except Exception:
					pass
				try:
					await j
				except asyncio.CancelledError:
					if self.root.verbose:
						print(j.name,'*CANCELLED*', sep='\t', file=self.stdout)
				except Exception:
					log_exception("Cancelling %s",j.name)

		return len(jobs)


