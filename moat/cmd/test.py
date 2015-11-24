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

"""Run tests, which incidentally also sets up the system if you use '-f'."""

import os
import sys
from moat.script import Command, CommandError
from moat.script.run import StdCommand
from etctree.util import from_etcd
import aioetcd as etcd
import asyncio
import time

import logging
logger = logging.getLogger(__name__)

__all__ = ['TestCommand']

class ConfigCommand(Command):
	name = "config"
	summary = "Verify configuration data"""
	description = """\
Check basic config layout.

"""

	def do(self,args):
		c = self.root.cfg
		try:
			c = c['config']
		except KeyError: # pragma: no cover
			raise CommandError("config: missing 'config' entry")

class EtcdCommand(StdCommand):
	name = "etcd"
	summary = "Verify etcd data"""
	description = """\
Check etcd access, and basic data layout.

"""

	def do(self,args):
		c = self.root.cfg['config']
		try:
			c = c['etcd']
		except KeyError:
			raise CommandError("config: missing 'etcd' section")
		for k in ('host','port','root'):
			if k not in c:
				raise CommandError("config.etcd: missing '%s' entry" % k) # pragma: no cover
		return self.root.sync(self._do())

	async def _do2(self, info):
		logger.debug("start: _do2")
		assert info == "Running tests"
		await asyncio.sleep(0.2,loop=self.root.loop)
		run_state = await self.run_state()

		t = time.time()
		assert run_state['started'] > t-int(os.environ.get('MOAT_IS_SLOW',1)), (run_state['started'],t)

	async def _do3(self):
		logger.debug("start: _do3")
		await asyncio.sleep(0.2,loop=self.root.loop)
		run_state = await self.run_state()
		raise RuntimeError("Dying")

	async def _do4(self):
		logger.debug("start: _do4")
		run_state = await self.run_state()
		async def _do4_():
			await asyncio.sleep(0.2,loop=self.root.loop)
			logger.debug("kill: _do4")
			await self.root.etcd.delete("/status/run/%s/%s/running"%(self.root.app,self.fullname))
		f = asyncio.ensure_future(_do4_(),loop=self.root.loop)
		try:
			logger.debug("sleep: _do4")
			await asyncio.sleep(2.0,loop=self.root.loop)
			raise RuntimeError("Did not get killed") # pragma: no cover
		finally:
			logger.debug("stop: _do4 %s",f)
			if not f.done():
				f.cancel() # pragma: no cover
			try: await f
			except Exception: pass # pragma: no cover

	async def _do(self):
		retval = 0
		etc = await self.root._get_etcd()
		log = logging.getLogger("etcd")
		stats = set(("ok","warn","error","fail"))
		s = await etc.tree("/status")
		if "run" not in s:
			log.error("missing 'run' entry")
			if self.parent.fix:
				await s.set("run",dict()) # pragma: no cover
			else:
				retval += 1
		if "errors" not in s:
			log.error("missing 'errors' entry")
			if self.parent.fix:
				await s.set("errors",dict((s,0) for s in stats))
			else:
				retval += 1
		if "errors" in s:
			err = s['errors']
			for stat in stats:
				if stat not in err:
					log.error("missing 'errors.%s' entry" % stat)
					if self.parent.fix:
						await err.set(stat,0)
					else:
						retval += 1

		await s._wait()
		try:
			await self.run(self._do3)
		except RuntimeError:
			pass
		else:
			raise RuntimeError("Error did not propagate") # pragma: no cover
		run_state = await self.run_state()
		if 'running' in run_state:
			raise RuntimeError("Procedure end 2 did not take") # pragma: no cover
		await s._wait()
		assert run_state['stopped'] > run_state['started']
		assert run_state['state'] == "error"

		try:
			await self.run(self._do4)
		except RuntimeError:
			pass
		else:
			raise RuntimeError("CancelledError did not propagate") # pragma: no cover
		run_state = await self.run_state()
		if 'running' in run_state:
			raise RuntimeError("Procedure end 2 did not take") # pragma: no cover
		await s._wait()
		assert run_state['stopped'] > run_state['started']
		assert run_state['state'] == "fail"

		f = asyncio.ensure_future(self.run(self._do2,"Running tests"), loop=self.root.loop)
		await asyncio.sleep(0.1,loop=self.root.loop)
		try:
			await self.run(self._do2,"Running tests", loop=self.root.loop)
		except RuntimeError as exc:
			assert exc.args[0] == "Run marker already exists"
		else:
			assert false,"Dup run didn't" # pragma: no cover
		await f
		run_state = await self.run_state()
		if 'running' in run_state:
			raise RuntimeError("Procedure end did not take") # pragma: no cover
		await s._wait()
		assert run_state['stopped'] > run_state['started']
		assert run_state['state'] == "ok"

		try:
			errs = await etc.read("/status/errors")
		except etcd.EtcdKeyNotFound:
			if self.parent.fix:
				raise RuntimeError("Creating /errors did not take. Duh?") # pragma: no cover ## hopefully
			# otherwise it's not there and there's nothing to do
		else:
			pass

		return retval

class AmqpCommand(Command):
	name = "amqp"
	summary = "Verify amqp data"
	description = """\
Check amqp access, and basic queue layout.

Note that starting the AMQP connector automatically creates the requisite
exchanges and queues.

"""

	def do(self,args):
		pass

class KillCommand(Command):
	name = "Kill"
	description = """\
Kill off all data.

Only when testing!
"""

	def do(self,args):
		if not self.root.cfg['config'].get('testing',False) or \
		   len(args) != 2 or " ".join(args) != "me hardeR":
			raise CommandError("You're insane.")
		etc = self.root.sync(self.root._get_etcd())
		self.log.fatal("Erasing your etcd data in three seconds.")
		time.sleep(3)
		self.root.sync(etc.delete("/",recursive=True))
		self.log.warn("All gone.")
		return

class TestCommand(Command):
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
		AmqpCommand,
	]
	fix = False

	def addOptions(self):
		self.parser.add_option('-f','--fix',
            action="store_true", dest="fix",
            help="try to fix problems")

	def handleOptions(self):
		self.fix = self.options.fix

	def do(self,args):
		if self.root.cfg['config'].get('testing',False):
			print("NOTE: this is a test configuration.", file=sys.stderr)
		else: # pragma: no cover ## not doing the real thing here
			print("WARNING: this is NOT a test.", file=sys.stderr)
			time.sleep(3)

		res = 0
		for c in self.subCommandClasses:
			if c.summary is None:
				continue
			if self.root.verbose > 1:
				print("Checking:",c.name)
			c = c(parent=self)
			try:
				res |= (c.do(args) or 0)
			except Exception as exc: # pragma: no cover
				if self.root.verbose > 1:
					import traceback
					traceback.print_exc(file=sys.stderr)
					return 9
				raise CommandError("%s failed: %s" % (c.name,repr(exc)))
		if self.root.verbose:
			print("All tests done.")
		return res

