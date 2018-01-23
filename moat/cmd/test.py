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
from collections.abc import Mapping

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

_do2_running = None

class EtcdCommand(Command):
	name = "etcd"
	summary = "Verify etcd data"""
	description = """\
Check etcd access, and basic data layout.

"""

	class Task_do2(Task):
		async def task(self):
			logger.debug("start: _do2")
			_do2_running.set()
			await asyncio.sleep(0.3,loop=self.loop)

			t = time.time()
			run_state = await _run_state(self.tree,('test','do_2'))
			assert run_state['started'] > t-int(os.environ.get('MOAT_IS_SLOW',1)), (run_state['started'],t)

	class Task_do3(Task):
		async def task(self):
			logger.debug("start: _do3")
			await asyncio.sleep(0.2,loop=self.loop)
			raise RuntimeError("Dying – triggered by testing, not an error")

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
		log = logging.getLogger(__name__+".etcd")
		show = log.info if self.parent.fix else log.warning

		s = None
		try:
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
		s = await etc.tree("/status", immediate=None)
		try:
			if "run" not in s:
				show("missing 'run' entry")
				if self.parent.fix:
					await s.set("run",dict()) # pragma: no cover
				else:
					retval += 1
			if "error" not in s:
				show("missing 'error' entry")
				if self.parent.fix:
					await s.set("error",dict())
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

			logger.error("The following 'Job is already running' message is part of the test.")
			global _do2_running
			_do2_running = asyncio.Event(loop=self.root.loop)
			dt2 = self.Task_do2(self,"test/do_2",{})
			await s.wait()
			dt2.run_state = run_state = await _run_state(tree,('test','do_2'))
			try:
				await asyncio.wait_for(_do2_running.wait(), 10,loop=self.root.loop)
			except asyncio.TimeoutError:
				import pdb;pdb.set_trace()
				raise

			dt2a = self.Task_do2(self,"test/do_2",{})
			try:
				await dt2a
			except JobIsRunningError as exc:
				assert exc.args[0] == "test/do_2", exc
			else:
				raise RuntimeError("Dup run didn't") # pragma: no cover
			await dt2
			if 'running' in run_state:
				raise RuntimeError("Procedure end did not take") # pragma: no cover
			await s.wait()
			assert run_state['stopped'] > run_state['started'], (run_state['stopped'], run_state['started'])
			assert run_state['state'] == "ok", run_state['state']

			try:
				errs = await etc.read("/status/error")
			except etcd.EtcdKeyNotFound:
				if self.parent.fix:
					raise RuntimeError("Creating /status/error did not take. Duh?") # pragma: no cover ## hopefully
				# otherwise it's not there and there's nothing to do
			else:
				pass

		finally:
			await s.close()
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
		log = logging.getLogger(__name__+".types")
		from moat.types import types,TYPEDEF_DIR,TYPEDEF
		tree = await etc.tree(TYPEDEF_DIR)
		for t in types():
			path = tuple(t.name.split('/'))
			if self.root.verbose:
				try:
					d = await tree.subdir(path, name=TYPEDEF, create=False)
				except (KeyError,etcd.EtcdKeyNotFound):
					log.info("Creating %s",t.name)
					d = await tree.subdir(path, name=TYPEDEF, create=True)
				else:
					log.debug("Found %s",t.name)
			else:
				d = await tree.subdir(path, name=TYPEDEF)
			for k,v in t.vars.items():
				if k not in d:
					await d.set(k,str(v))
		await tree.close()

class DefaultsCommand(Command):
	name = "defaults"
	summary = "Add known default data (and their types) for tasks to etcd"
	description = """\
		In etcd, /meta/task/:default contains the default settings for tasks.

		This command fills that data.
		"""

	async def do(self,args):
		etc = await self.root._get_etcd()
		log = logging.getLogger(__name__+".defaults")
		from moat.types import types,TYPEDEF_DIR,TYPEDEF
		from moat.task import TASKDEF_DIR, TASKDEF_DEFAULT, TASK_TYPE,TASK_DATA
		tree = await self.root._get_tree()
		show = log.info if self.parent.fix else log.warning
		fshow = log.info if self.parent.force else log.warning

		from moat.script.main import DEFAULT_CONFIG
		mt = await tree.subdir(TYPEDEF_DIR)
		r = await tree.subdir(TASKDEF_DIR, name=TASKDEF_DEFAULT)
		rt = await r.subdir(TASK_TYPE)
		rv = await r.subdir(TASK_DATA)

		async def do_typ(rt,data):
			m = None
			for k,v in data.items():
				if isinstance(v,Mapping):
					m = await do_typ(await rt.subdir(k), v)
				else:
					t = type(v).__name__
					if t not in mt:
						raise RuntimeError("Don't know the type for %s" % (repr(v),))
					if k not in rt:
						show("missing type: %s=%s",k,t)
						if self.parent.fix:
							m = await rt.set(k,t)
					elif rt[k].value != t:
						fshow("difference for %s: %s / %s", k,rt[k],t)
						if self.parent.force:
							m = await rt.set(k,t)
			return m

		async def do_val(rt,data):
			m = None
			for k,v in data.items():
				if isinstance(v,Mapping):
					m = await do_val(await rv.subdir(k), v)
				elif k not in rv:
					show("missing value: %s=%s",k,v)
					if self.parent.fix:
						m = await rv.set(k,v)
				elif rv[k] != v:
					fshow("difference for %s: %s / %s", k,rv[k],v)
					if self.parent.force:
						m = await rv.set(k,v)

			return m

		m = await do_typ(rt,DEFAULT_CONFIG['run'])
		await rt.wait(m, tasks=True)
		m = await do_val(rv,DEFAULT_CONFIG['run'])

class ErrorsCommand(Command):
	name = "error"
	summary = "Check error message consistency"
	description = """\
		/status/error contains a list of errors.

		This command curries that list, i.e. removes obsolete entires.
		"""

	async def do(self,args):
		log = logging.getLogger(__name__+".errors")
		show = log.info if self.parent.fix else log.warning
		etc = await self.root._get_etcd()
		s = await self.root._get_tree()
		from moat.types import ERROR_DIR
		from moat.types.error import ErrorMismatch
		err = await s.lookup(ERROR_DIR)
		retval = 0
		for etyp in list(err.values()):
			etyp = await etyp
			for edir in list(etyp.values()):
				edir = await edir
				try:
					ptr = await edir.get_ptr(check=True)
				except ErrorMismatch:
					ptr = None
				if ptr is None:
					show("Error obsolete: %s",edir)
					ptr = await edir.get_ptr(check=True)
					if self.parent.fix:
						await edir.delete()
					else:
						retval += 1
				elif self.root.verbose:
					print(etyp.name,edir['loc'].value,edir['msg'])
		return retval

class WebCommand(Command):
	name = "web"
	summary = "Add known web types to etcd"
	description = """\
		In etcd, /meta/web contains a list of known display methods.

		This command fills that list.
		"""

	async def do(self,args):
		etc = await self.root._get_etcd()
		log = logging.getLogger(__name__+".web")
		from moat.web import webdefs,WEBDEF_DIR,WEBDEF
		show = log.info if self.parent.fix else log.warning
		fshow = log.info if self.parent.force else log.warning
		for t in webdefs():
			path = tuple(t.name.split('/'))
			d = None
			if self.root.verbose:
				try:
					d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,), create=False)
				except etcd.EtcdKeyNotFound:
					if self.parent.fix:
						show("Creating %s",t.name)
						d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,), create=True)
					else:
						show("Not found: %s, skipping",t.name)
						continue
				else:
					log.debug("Found %s",t.name)
			else:
				d = await etc.tree(WEBDEF_DIR+path+(WEBDEF,))

			try:
				for k,v in t.vars.items():
					v = str(v)
					if k not in d:
						show("missing value: %s=%s",k,v)
						if self.parent.fix:
							await d.set(k,v)
					elif d[k] != v:
						fshow("difference for %s: %s / %s", k,d[k],v)
						if self.parent.force:
							await d.set(k,v)
						
			finally:
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
		DefaultsCommand,
		ErrorsCommand,
		WebCommand,
		AmqpCommand,
	]
	fix = False

	def addOptions(self):
		self.parser.add_option('-f','--fix',
			action="store_true", dest="fix",
			help="try to fix problems")
		self.parser.add_option('-F','--force',
			action="store_true", dest="force",
			help="replace changes with defaults")

	def handleOptions(self):
		self.fix = self.options.fix
		self.force = self.options.force

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

