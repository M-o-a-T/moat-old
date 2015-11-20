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
import sys
from moat.script import Command, CommandError
from etctree.util import from_etcd
import aioetcd as etcd
import asyncio
import logging

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
		except KeyError:
			raise CommandError("config: missing 'config' entry")

class EtcdCommand(Command):
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
				raise CommandError("config.etcd: missing '%s' entry" % k)
		self.root.sync(self._do())
	
	async def _do(self):
		etcd = await self.root._get_etcd()
		log = logging.getLogger("etcd")
		stats = set(("ok","warn","error","fail"))
		s = await etcd.tree("/status")
		if "run" not in s:
			log.error("missing 'run' entry")
			if self.parent.fix:
				await s.set("run",dict())
		if "errors" not in s:
			log.error("missing 'errors' entry")
			if self.parent.fix:
				await s.set("errors",dict((s,0) for s in stats))
		else:
			err = s['errors']
			for stat in stats:
				if stat not in err:
					log.error("missing 'errors.%s' entry" % stat)
					if self.parent.fix:
						await err.set(stat,0)

		await s._wait()

		await self.state("test","warn","Running tests")
		errs = await etcd.read("/errors")
		import pdb;pdb.set_trace()
		pass



class AmqpCommand(Command):
	name = "amqp"
	summary = "Verify amqp data"""
	description = """\
Check amqp access, and basic queue layout.

Note that starting the AMQP connector automatically creates the requisite
exchanges and queues.

"""

	def do(self,args):
		pass

class TestCommand(Command):
	name = "test"
	summary = "Run various tests"""
	description = """\
Set some data.
"""

	# process in order
	subCommandClasses = [
		ConfigCommand,
		EtcdCommand,
		AmqpCommand,
	]
	fix = False

	def addOptions(self):
		self.parser.add_option('-f','--fix',
            action="store_true", dest="fix",
            help="try to fix problems")

	def handleOptions(self,opts):
		self.fix = opts.fix
	
	def do(self,args):
		if self.root.cfg['config'].get('testing',False):
			print("NOTE: this is a test configuration.", file=sys.stderr)

		for c in self.subCommandClasses:
			if self.root.verbose > 1:
				print("Checking:",c.name)
			c = c(parent=self)
			try:
				c.do(args)
			except Exception as exc:
				if self.root.verbose > 1:
					import traceback
					traceback.print_exc(file=sys.stderr)
					return
				raise CommandError("%s failed: %s" % (c.name,repr(exc)))
		if self.root.verbose:
			print("All tests done.")
		
