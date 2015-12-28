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

"""Run known Tasks"""

import asyncio
import os
import signal
import sys

from ..script import Command, CommandError
from ..script.task import TaskMaster, JobIsRunningError, JobMarkGoneError
from ..task import TASK_DIR,TASK, TASKSTATE_DIR,TASKSTATE, task_state_types
from moat.util import r_dict
from yaml import safe_dump
from datetime import datetime
from etcd_tree.util import from_etcd
from etcd_tree.etcd import EtcTypes
from etcd_tree.node import EtcDir,EtcFloat
from functools import partial
from itertools import chain
import aio_etcd as etcd
import traceback

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

	def _tilt(self):
		self.root.loop.remove_signal_handler(signal.SIGINT)
		self.root.loop.remove_signal_handler(signal.SIGTERM)
		self.tilt.set_result(None)

	async def process_task(self, path):
		if path in self.seen:
			return
		self.seen.add(path)

	async def do_async(self,args):
		self.seen = set()
		self.tilt = asyncio.Future(loop=self.root.loop)
		opts = self.options
		if opts.is_global and not args:
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
		self.args = args
		self.paths = []
		self._monitors = []
		self.tasks = []
		self.jobs = {}
		self.rescan = asyncio.Future(loop=self.root.loop)
		for t in self.args:
			tree = await etc.tree(t)
			self.paths.append(tree)
			self._monitors.append(tree.add_monitor(self._rescan))
		await self._scan()
		if not self.tasks:
			if self.root.verbose:
				print("No tasks found. Exiting.", file=sys.stderr)
			return

		self.root.loop.add_signal_handler(signal.SIGINT,self._tilt)
		self.root.loop.add_signal_handler(signal.SIGTERM,self._tilt)
		await self._start()
		return (await self._loop())

	async def _loop(self):
		errs = 0
		try:
			while self.jobs:
				done,pending = await asyncio.wait(chain((self.tilt,self.rescan),self.jobs.values()), loop=self.root.loop, return_when=asyncio.FIRST_COMPLETED)
				for j in done:
					if j in (self.tilt,self.rescan):
						continue
					del self.jobs[j.name]
					try:
						r = j.result()
					except asyncio.CancelledError:
						errs += 10
						if self.root.verbose:
							print(j.name,'*CANCELLED*', sep='\t', file=self.stdout)
					except Exception as exc:
						errs += 1
						logger.exception("Running %s",j.name)
						if self.options.killfail:
							break
					else:
						if self.root.verbose > 1:
							print(j.name,r, sep='\t', file=self.stdout)
				if self.tilt.done():
					break
				if self.rescan.done():
					self.rescan = asyncio.Future(loop=self.root.loop)
					await self._scan()
					await self._start()

		finally:
			for j in self.jobs.values():
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
		return errs

		
	def _rescan(self,_=None):
		if not self.rescan.done():
			self.rescan.set_result(None)

	async def _scan(self):
		depth = self.options.this
		p = self.paths
		while p and depth != 1:
			depth -= 1
			n_p = []
			for t in p:
				for k,v in t.items():
					if k == TASK:
						if depth < 2:
							self.tasks.append(v)
					elif k.startswith(':'):
						continue
					elif isinstance(v,EtcDir):
						n_p.append(v)
			p = n_p

	async def _start(self):
		def _report(path, state, *value):
			if self.root.verbose:
				if state == "error" and value:
					err = value[0]
					if isinstance(err,JobIsRunningError):
						errs = "already running"
						err = None
					elif isinstance(err,JobMarkGoneError):
						errs = "task lock broken ?!?"
						err = None
					else:
						errs = repr(err)
					print(path,state, errs, sep='\t', file=self.stdout)
					if self.root.verbose > 1 and err is not None:
						traceback.print_exception(err.__class__,err,err.__traceback__)
				else:
					print(path,state, *value, sep='\t', file=self.stdout)

		js = {}
		old = set(self.jobs)
		while self.tasks:
			t = self.tasks.pop()
			path = t.path[len(TASK_DIR)+1:-(len(TASK)+1)]
			if path in old:
				old.remove(path)
				continue

			try:
			    j = TaskMaster(self, path, callback=partial(_report, path))
			except Exception as exc:
				logger.exception("Could not set up %s (%s)",t.path,t.get('name',path))
				if opts.killfail:
					return 2
			else:
				js[j.path] = (t,j)

		for name,tj in js.items():
			t,j = tj
			try:
				await j.init()
			except JobIsRunningError:
				continue
			except Exception as exc:
				# Let's assume that this is fatal.
				await self.root.etcd.set('/'.join((TASKSTATE_DIR,j.path,TASKSTATE,"debug")), "".join(traceback.format_exception(exc.__class__,exc,exc.__traceback__)))
				logger.exception("Could not init %s (%s)",t.path,t.get('name',path))
				if self.options.killfail:
					for j in self.jobs.values():
						j.cancel()
					return 2
			else:
				self.jobs[j.name] = j

		for path in old:
			await self.jobs[path].cancel()

		return len(self.jobs)


