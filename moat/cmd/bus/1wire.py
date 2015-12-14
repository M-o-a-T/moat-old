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

"""Commands to setup and modify tasks"""

import os
import sys
from moat.script import Command, CommandError
from moat.script.task import Task
from moat.task import tasks
from moat.util import r_dict
from etcd_tree.util import from_etcd
from etcd_tree.etcd import EtcTypes
from etcd_tree.node import mtInteger
from yaml import safe_dump
import aioetcd as etcd
import asyncio
import time
import types as py_types
import etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['OneWireCommand']

class ServerAddCommand(Command):
	name = "add"
	summary = "Add a 1wire server"
	description = """\
Tell MoaT about an 1wire server (OWFS).

Arguments:

* human-readable server name 

* host name, or IP address

* port number (optional, default is 4304)
"""

	def addOptions(self):
		self.parser.add_option('-u','--update',
            action="store_true", dest="update",
            help="update an existing entry")

	def handleOptions(self):
		self.update = self.options.update

	async def do_async(self,args):
		await self.root.setup(self)
		if len(args) < 2:
			raise CommandError("Usage: … add ‹name› ‹host› [‹port›]")
		name = args[0]
		if ':' in name or '/' in name:
			raise CommandError("The service name can't contain colons or slashes.")
		host = args[1]
		try:
			if args[2] == '-':
				port = 4304
			else:
				port = int(args[2])
		except IndexError:
			port = 4304
		except ValueError:
			raise CommandError("The port must be an integer")
		else:
			if port<1 or port>65534:
				raise CommandError("The port must be positive and <65535")

		types = EtcTypes()
		types.register('port',mtInteger)
		try:
			t = await self.root.etcd.tree('/bus/onewire/server/'+name, types=types, create=not self.update)
		except etcd.EtcdAlreadyExist:
			raise CommandError("Host '%s' exists. Use '-u' or choose a different name." % name)
		except etcd.EtcdKeyNotFound:
			raise CommandError("Host '%s' does not exist. Drop '-u' or choose an existing name." % name)
		await t.set('host',host)
		await t.set('port',port)
		if len(args) > 3:
			await t.set('info',' '.join(args[3:]))
		if self.root.verbose > 1:
			print(name, "updated" if self.update else "created", file=self.stdout)

class ServerListCommand(Command):
	name = "list"
	summary = "List 1wire servers"
	description = """\
List 1wire servers (OWFS) known to MoaT.
If you name a server, details are shown in YAML format,
else a short list is printed.
"""

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if args:
			dirs = args
		else:
			dirs = []
			res = await etc.get('/bus/onewire/server')
			for r in res.children:
				dirs.append(r.key.rsplit('/',1)[1])
		for d in dirs:
			if self.root.verbose > 1:
				st = await etc.tree('/bus/onewire/server/'+d, static=True)
				safe_dump({d: r_dict(dict(st))}, stream=self.stdout)
			elif self.root.verbose:
				h = await etc.get('/bus/onewire/server/'+d+'/host')
				p = await etc.get('/bus/onewire/server/'+d+'/port')
				print(d,h.value,p.value, sep='\t', file=self.stdout)
			else:
				print(d, file=self.stdout)

class ServerDeleteCommand(Command):
	name = "delete"
	summary = "Delete a 1wire server"
	description = """\
Make MoaT forget about a 1wire server.
"""

	def addOptions(self):
		self.parser.add_option('-f','--force',
			action="store_true", dest="force",
			help="not forcing won't do anything")

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = []
			res = etc.get('/bus/onewire/server')
			for r in res.children:
				args.append(r.name.rsplit('/',1)[1])
		for k in args:
			await etc.delete('/bus/onewire/server/'+k, recursive=True)
			if self.root.verbose > 1:
				print("%s: deleted"%k, file=self.stdout)

class ServerCommand(Command):
	subCommandClasses = [
		ServerAddCommand,
		ServerListCommand,
		ServerDeleteCommand,
	]
	name = "server"
	summary = "OWFS server specific subcommands"
	description = """\
Commands to set up and admin connections to 1wire servers (OWFS).
"""


class OneWireCommand(Command):
	name = "1wire"
	summary = "Configure and define tasks"
	description = """\
Commands to set up and admin the task list known to MoaT.
"""

	subCommandClasses = [
		ServerCommand,
	]

