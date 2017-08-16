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

"""Run tests, which incidentally also sets up the system if you use '-f'."""

import os
import sys
import aio_etcd as etcd
import asyncio
import time
import types

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task,_run_state, JobMarkGoneError,JobIsRunningError
from moat.task import TASKSTATE_DIR,TASKSTATE, TASKSCAN_DIR,TASK

import logging
logger = logging.getLogger(__name__)

__all__ = ['TestCommand']

class ConfigCommand(Command):
	name = "config"
	summary = "Verify configuration data"""
	description = """\
Check basic config layout.

"""

	async def do(self,args):
		c = self.root.cfg
		try:
			c = c['config']
		except KeyError: # pragma: no cover
			raise CommandError("config: missing 'config' entry")

class EtcdCommand(Command):
	name = "etcd"
	summary = "Verify etcd data"""
	description = """\
Check etcd access, and basic data layout.

"""

	class Task_do2(Task):
		async def task(self):
			logger.debug("start: _do2")
			await asyncio.sleep(0.3,loop=self.loop)

			t = time.time()
			run_state = await _run_state(self.tree,('test','do_2'))
			assert run_state['started'] > t-int(os.environ.get('MOAT_IS_SLOW',1)), (run_state['started'],t)

	class Task_do3(Task):
		async def task(self):
			logger.debug("start: _do3")
			await asyncio.sleep(0.2,loop=self.loop)
			print("The following RuntimeError is part of the test.",file=sys.stderr)
			raise RuntimeError("Dying")

	class Task_do4(Task):
		async def task(self):
			logger.debug("start: _do4")
			async def _do4_():
				await asyncio.sleep(0.2,loop=self.loop)
				logger.debug("kill: _do4")
				await self.etcd.delete(TASKSTATE_DIR+('test','do_4',TASKSTATE,'running'))
			f = asyncio.ensure_future(_do4_(),loop=self.loop)
			try:
				logger.debug("sleep: _do4")
				await asyncio.sleep(2.0,loop=self.loop)
				raise RuntimeError("Did not get killed") # pragma: no cover
			finally:
				logger.debug("stop: _do4 %s",f)
				if not f.done():
					logger.info('CANCEL 4 %s',f)
					f.cancel() # pragma: no cover
				try: await f
				except Exception: pass # pragma: no cover

	async def do(self,args):
		c = self.root.cfg['config']
		try:
			c = c['etcd']
		except KeyError:
			raise CommandError("config: missing 'etcd' section")
		for k in ('host','port','root'):
			if k not in c:
				raise CommandError("config.etcd: missing '%s' entry" % k) # pragma: no cover

		retval = 0
		etc = await self.root._get_etcd()
		tree = await self.root._get_tree()
		log = logging.getLogger("etcd")
		show = log.info if self.parent.fix else log.warning

		try:
			s = None
			s = await etc.tree('/config')
			await s.subdir('run', create=False)
		except KeyError:
			show("/config/run created.")
			if self.parent.fix:
				await s.subdir('run',create=True)
			else:
				retval += 1
		finally:
			if s is not None:
				await s.close()

		stats = set(("ok","warn","error","fail"))
		s = await etc.tree("/status")
		if "run" not in s:
			show("missing 'run' entry")
			if self.parent.fix:
				await s.set("run",dict()) # pragma: no cover
			else:
				retval += 1
		if "errors" not in s:
			show("missing 'errors' entry")
			if self.parent.fix:
				await s.set("errors",dict((stat,0) for stat in stats))
			else:
				retval += 1
		else:
			err = s['errors']
			for stat in stats:
				if stat not in err:
					show("missing 'errors.%s' entry" % stat)
					if self.parent.fix:
						await err.set(stat,0)
					else:
						retval += 1

		await s.wait()
		if not self.root.cfg['config'].get('testing',False):
			return

		# The next part is test environment only
		try:
			t = self.Task_do3(self,"test/do_3")
			await t
		except RuntimeError as exc:
			pass
		else:
			raise RuntimeError("Error did not propagate") # pragma: no cover
		run_state = await _run_state(tree,('test','do_3'))
		if 'running' in run_state:
			raise RuntimeError("Procedure end 2 did not take") # pragma: no cover
		await s.wait()
		assert run_state['stopped'] > run_state['started'], (run_state['stopped'], run_state['started'])
		assert run_state['state'] == "error", run_state['state']

		try:
			t = self.Task_do4(self,"test/do_4",_ttl=3,_refresh=10)
			await t
		except JobMarkGoneError:
			pass
		else:
			raise RuntimeError("Cancellation ('running' marker gone) did not propagate") # pragma: no cover
		run_state = await _run_state(tree,('test','do_4'))
		assert 'running' not in run_state
		await s.wait()
		assert run_state['stopped'] > run_state['started'], (run_state['stopped'], run_state['started'])
		assert run_state['state'] == "fail", run_state['state']

		print("The following 'Job is already running' message is part of the test.",file=sys.stderr)
		dt2 = self.Task_do2(self,"test/do_2",{})
		await s.wait()
		dt2.run_state = run_state = await _run_state(tree,('test','do_2'))
		await asyncio.sleep(0.1,loop=self.root.loop)
		dt2a = self.Task_do2(self,"test/do_2",{})
		await asyncio.sleep(0.1,loop=self.root.loop)
		try:
			await dt2a
		except JobIsRunningError as exc:
			assert exc.args[0] == "test/do_2", exc
		else:
			assert False,"Dup run didn't" # pragma: no cover
		await dt2
		if 'running' in run_state:
			raise RuntimeError("Procedure end did not take") # pragma: no cover
		await s.wait()
		assert run_state['stopped'] > run_state['started'], (run_state['stopped'], run_state['started'])
		assert run_state['state'] == "ok", run_state['state']

		try:
			errs = await etc.read("/status/errors")
		except etcd.EtcdKeyNotFound:
			if self.parent.fix:
				raise RuntimeError("Creating /errors did not take. Duh?") # pragma: no cover ## hopefully
			# otherwise it's not there and there's nothing to do
		else:
			pass

		return retval

class TypesCommand(Command):
	name = "types"
	summary = "Add known data types to etcd"
	description = """\
		In etcd, /meta/types contains a list of known data types.

		This command fills that list.
		"""

	async def do(self,args):
		etc = await self.root._get_etcd()
		from moat.types import types,TYPEDEF_DIR,TYPEDEF
		for t in types():
			path = tuple(t.name.split('/'))
			if self.root.verbose:
				try:
					d = await etc.tree(TYPEDEF_DIR+path+(TYPEDEF,), create=False)
				except etcd.EtcdKeyNotFound:
					logger.info("Creating %s",t.name)
					d = await etc.tree(TYPEDEF_DIR+path+(TYPEDEF,), create=True)
				else:
					logger.debug("Found %s",t.name)
			else:
				d = await etc.tree(TYPEDEF_DIR+path+(TYPEDEF,))
			for k,v in t.vars.items():
				if k not in d:
					await d.set(k,v)
			await d.close()

class WebCommand(Command):
	name = "web"
	summary = "Add known web types to etcd"
	description = """\
		In etcd, /meta/web contains a list of known display methods.

		This command fills that list.
		"""

	async def do(self,args):
		etc = await self.root._get_etcd()
		from moat.web import webdefs,WEBDEF_DIR,WEBDEF
		for t in webdefs():
			path = tuple(t.name.split('/'))
			if self.root.verbose:
				try:
					d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,), create=False)
				except etcd.EtcdKeyNotFound:
					logger.info("Creating %s",t.name)
					d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,), create=True)
				else:
					logger.debug("Found %s",t.name)
			else:
				d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,))

			for k,v in t.vars.items():
				if k not in d:
					await d.set(k,v)
			await d.close()

class AmqpCommand(Command):
	name = "amqp"
	summary = "Verify amqp data"
	description = """\
Check amqp access, and basic queue layout.

Note that starting the AMQP connector automatically creates the requisite
exchanges and queues.

"""

	async def do(self,args):
		pass

class KillCommand(Command):
	name = "Kill"
	description = """\
Kill off all data.

This command only works when testing.
"""

	async def do(self,args):
		if not self.root.cfg['config'].get('testing',False) or \
		   len(args) != 2 or " ".join(args) != "me hardeR":
			raise CommandError("You're insane.")
		etc = await self.root._get_etcd()
		self.log.fatal("Erasing your etcd data in three seconds.")
		time.sleep(3)
		await etc.delete("/",recursive=True)
		self.log.warn("All gone.")
		return

class TestCommand(SubCommand):
	name = "test"
	summary = "Run various tests"""
	description = """\
Set some data.
"""

	# process in order
	subCommandClasses = [
		KillCommand,
		ConfigCommand,
		EtcdCommand,
		TypesCommand,
		WebCommand,
		AmqpCommand,
	]
	fix = False

	def addOptions(self):
		self.parser.add_option('-f','--fix',
            action="store_true", dest="fix",
            help="try to fix problems")

	def handleOptions(self):
		self.fix = self.options.fix

	async def do(self,args):
		if self.root.cfg['config'].get('testing',False):
			print("NOTE: this is a test configuration.", file=sys.stderr)
		else: # pragma: no cover ## not doing the real thing here
			print("WARNING: this is NOT a test.", file=sys.stderr)
			time.sleep(3)

		if args:
			return (await super().do(args))

		res = 0
		for c in self.subCommandClasses:
			if c.summary is None:
				continue
			if self.root.verbose > 1:
				print("Checking:",c.name)
			c = c(parent=self)
			try:
				res = (await c.do(args) or 0)
			except Exception as exc: # pragma: no cover
				if self.root.verbose > 1:
					import traceback
					traceback.print_exc(file=sys.stderr)
					return 9
				raise CommandError("%s failed: %s" % (c.name,repr(exc)))
			else:
				if res:
					print("Error. Stopped test run.", file=sys.stderr)
					return res
		if self.root.verbose:
			print("All tests done.", file=self.stdout)
		return res

