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
from contextlib import suppress

from ..script import Command, CommandError
from ..script.task import TaskMaster, JobIsRunningError, JobMarkGoneError
from ..task import TASK_DIR,TASK, TASKSTATE_DIR,TASKSTATE
from etcd_tree.node import EtcDir
from functools import partial
from itertools import chain
import traceback

import logging
logger = logging.getLogger(__name__)

__all__ = ['RunCommand']

class RunCommand(Command):
	name = "run"
	summary = "Start tasks"""
	description = """\
Run MoaT tasks.

"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
            action="count", dest="this", default=0,
            help="Run the given job only (-tt for jobs one level below, etc.)")
		self.parser.add_option('-g','--global',
            action="store_true", dest="is_global",
            help="Do not prepend the appname to the paths")
		self.parser.add_option('-o','--one-shot',
            action="count", dest="oneshot", default=0,
            help="Do not restart. Twice: Do not retry.")
		self.parser.add_option('-q','--quit',
            action="store_true", dest="quit",
            help="Do not watch etcd.")
		self.parser.add_option('-s','--single',
            action="store_true", dest="single",
            help="one path argument given (may contain spaces)")

	def _tilt(self):
		self.root.loop.remove_signal_handler(signal.SIGINT)
		self.root.loop.remove_signal_handler(signal.SIGTERM)
		self.tilt.set_result(None)

	async def process_task(self, path):
		if path in self.seen:
			return
		self.seen.add(path)

	async def do(self,args):
		res = 0
		self.seen = set()
		self.tilt = asyncio.Future(loop=self.root.loop)
		opts = self.options
		if opts.is_global and not args:
			raise CommandError("You can't run the whole world.")

		etc = await self.root._get_etcd()
		tree = await self.root._get_tree()
		if args:
			if opts.single and len(args) > 1:
				args = (' '.join(args),)
			if not opts.is_global:
				args = [self.root.app+'/'+t for t in args]
			args = [TASK_DIR+tuple(t.split('/')) for t in args]
		else:
			if opts.single:
				raise CommandError("Not passing a path with '--single' does not make sense.")
			if opts.is_global:
				args = [TASK_DIR]
			else:
				args = [TASK_DIR+(self.root.app,)]
		self.args = args
		self.paths = []
		self._monitors = []
		self.tasks = []
		self.jobs = {}
		self.rescan = asyncio.Future(loop=self.root.loop)
		for t in self.args:
			try:
				tree = await tree.subdir(t, create=False)
			except KeyError as err:
				print("Unknown: "+'/'.join(err.args[0]), file=sys.stderr)
				res = 2
			else:
				self.paths.append(tree)
				self._monitors.append(tree.add_monitor(self._rescan))
		if res:
			return res
		await self._scan()
		if not self.tasks:
			if self.root.verbose:
				print("No tasks found. Exiting.", file=sys.stderr)
			return 1

		self.root.loop.add_signal_handler(signal.SIGINT,self._tilt)
		self.root.loop.add_signal_handler(signal.SIGTERM,self._tilt)
		await self._start()
		return (await self._loop())

	async def _loop(self):
		errs = 0
		try:
			while self.jobs:
				logger.debug("Task Jobs %s",dict(self.jobs))
				done,pending = await asyncio.wait(chain((self.tilt,self.rescan),self.jobs.values()), loop=self.root.loop, return_when=asyncio.FIRST_COMPLETED)
				logger.debug("Task DP %s %s",done,pending)
				for j in done:
					if j in (self.tilt,self.rescan):
						continue
					del self.jobs[j.path]
					try:
						r = j.result()
					except asyncio.CancelledError:
						errs += 10
						logger.info('CANCELLED %s', j.name)
						if self.root.verbose:
							print(j.name,'*CANCELLED*', sep='\t', file=self.stdout)
					except Exception as exc:
						errs += 1
						logger.exception("Running %s", j.name)
						if self.root.verbose:
							print(j.name,'*ERROR*', exc, sep='\t', file=self.stdout)
						if self.options.oneshot:
							break
					else:
						logger.info('EXIT %s %s', j.name,r)
						if self.root.verbose > 1:
							print(j.name,r, sep='\t', file=self.stdout)
				if self.tilt.done():
					self.tilt.result() # re-raises any exception
					break
				if self.rescan.done():
					logger.debug("rescanning")
					self.rescan = asyncio.Future(loop=self.root.loop)
					await self._scan()
					await self._start()

		finally:
			try:
				logger.debug("NoMoreJobs")
			except NameError: # may occur when shutting down
				pass
			for j in self.jobs.values():
				try:
					logger.info('CANCEL 1 %s',j)
					await j.cancel_job()
				except Exception:
					pass
				try:
					await j
				except asyncio.CancelledError:
					if self.root.verbose:
						print(j.name,'*CANCELLED*', sep='\t', file=self.stdout)
					logger.debug("canceled %s",j.name)
				except Exception:
					logger.exception("Cancelling %s",j.name)
				else:
					logger.debug("ended %s",j.name)
		return errs

		
	def _rescan(self,_=None):
		if not self.rescan.done():
			logger.debug("rescanning")
			self.rescan.set_result(None)
		else:
			logger.debug("NOT rescanning")

	async def _scan(self):
		depth = self.options.this
		p = self.paths
		while p:
			depth -= 1
			n_p = []
			for t in p:
				for k,v in t.items():
					v = await v
					if k == TASK:
						if depth < 2:
							self.tasks.append(v)
					elif k.startswith(':'):
						continue
					elif isinstance(v,EtcDir):
						n_p.append(v)
			p = n_p
			if not depth:
				break

	async def _start(self):
		logger.debug("START")
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
					print('/'.join(path),state, errs, sep='\t', file=self.stdout)
				else:
					print('/'.join(path),state, *value, sep='\t', file=self.stdout)

		js = {}
		old = set(self.jobs)
		logger.debug("OLD %s",old)

		args = {}
		if self.options.oneshot:
			args['restart'] = 0
			if self.options.oneshot > 1:
				args['retry'] = 0
		if self.options.quit:
			args['one-shot'] = True

		while self.tasks:
			t = self.tasks.pop()
			path = t.path[len(TASK_DIR):-1]
			logger.debug("CHECK %s",path)
			if path in old:
				old.remove(path)
				continue

			logger.debug("Launch TM %s",path)
			try:
				j = TaskMaster(self, path, callback=partial(_report, path), **args)
			except Exception as exc:
				logger.exception("Could not set up %s (%s)",'/'.join(t.path),t.get('name',path))
				f = asyncio.Future(loop=self.root.loop)
				f.set_exception(exc)
				f.name = f.path = path
				self.jobs[path] = f
				if self.options.oneshot:
					return
			else:
				js[j.path] = (t,j)

		for name,tj in js.items():
			t,j = tj
			try:
				logger.debug("Init TM %s",j.path)
				await j.init()
			except JobIsRunningError:
				continue
			except Exception as exc:
				# Let's assume that this is fatal.
				await self.root.etcd.set(TASKSTATE_DIR+j.path+(TASKSTATE,"debug"), "".join(traceback.format_exception(exc.__class__,exc,exc.__traceback__)))
				f = asyncio.Future(loop=self.root.loop)
				f.set_exception(exc)
				f.name = f.path = j.path
				self.jobs[j.path] = f

				if self.options.oneshot:
					return
			else:
				logger.debug("AddJob TM %s",j.name)
				self.jobs[j.path] = j

		for path in old:
			j = self.jobs[path]
			logger.info('CANCEL 3 %s',j)
			j.cancel()
			with suppress(asyncio.CancelledError):
				await j


