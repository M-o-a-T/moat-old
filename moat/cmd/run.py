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

import os
from moat.script import Command, CommandError
from etctree.util import from_etcd
import aioetcd as etcd
import logging
logger = logging.getLogger(__name__)

__all__ = ['RunCommand']

class JobMaster(object):
	def __init__(self_,name,j,t, delay):
		self_.name = name
		self_.j = j
		self_.t = t
		super().__init__(loop=self.loop)
		self_.delay = self.loop.call_later(delay, self_.set_result,None)

	def cancel(self):
		if not self.done:
			self.delay.cancel()
			self.set_result(None)

class RunCommand(Command):
	name = "run"
	summary = "Start tasks"""
	description = """\
Run MoaT tasks.

by default, start every task that's defined for this host.

"""

	def addOptions(self):
		self.parser.add_option('-t','--this',
            action="count", dest="this",
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

	def do(self,args):
		retval = 0
		self.root.sync(self._do, args)
	
	async def _do(self,args):
		opts = self.options
		if opts.is_global and not args and not opts.list:
			raise CommandError("You can't run the whole world.")

		etc = await self.root._get_etcd()
		if args:
			if not self.opts.is_global:
				args = [cmd.app+'/'+t for t in args]
			args = ['/task/'+t for t in args]
		elif self.opts.is_global:
			args = ['/task/'+cmd.app]
		else:
			args = ['/task']
		
		tasks = []
		for t in args:
			tasks.append(await t.tree())
		depth = opts.this
		if depth > 1:
			while depth > 1:
				depth -= 1
				n_a = []
				for t in tasks:
					for k,v in t:
						if k.startswith(':'):
							continue
						n_a.append(v)
					tasks = n_a
			tasks = [t[':job'] for t in tasks if ':job' in t]
		else:
			n_a = []
			while tasks:
				t = tasks.pop()
				if ':job' in t:
					n_a.append(t[':job'])
				for k,v in t:
					if not k.startswith(':'):
						tasks.append(v)
		if opts.list:
			for t in sorted(tasks, key=lambda _:_.path):
				print(t.path,t['code'],t.get('summary',''), sep='\t')
			return

		jobs = {}
		for t in tasks:
			try:
				j = import_string(t['code'])
				j = j(self,t.path,t['data'], runner_data=t)
			except Exception as exc:
				logger.exception("Could not set up %s (%s)",t.path,t['code'])
				if opts.killfail:
					return 2
			else:
				jobs[j.name] = j

		try:
			while jobs:
				done,pending = await asyncio.wait(jobs.values(), loop=self.loop, return_when=FIRST_COMPLETED)
				for j in done:
					del jobs[j.name]
					if j.__class__ is Restarter:
						t = j.t
						j = j.j(self,t.path,t['data'], runner_data=t)
						jobs[j.name] = j
						continue
					try:
						r = j.result()
					except Exception as exc:
						log_exception("Running %s",j.name)
						if opts.killfail:
							break
					else:
						if self.root.verbose > 1:
							print(j.name,r, sep='\t', file=self.stdout)
					t = j.runner_data
					j = Restarter(j.name,j.__class__,t, 99)
					jobs[j.name] = j

		finally:
			for j in jobs.values():
				try:
					j.cancel()
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


