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

"""Commands to setup and modify tasks"""

import os
import sys

from etcd_tree.etcd import EtcTypes
from etcd_tree.node import EtcInteger
from yaml import safe_dump
from contextlib import suppress
import aio_etcd as etcd
import asyncio
import time
import types as py_types
import etcd

from moat.script import Command, SubCommand, CommandError
from moat.script.task import Task
from moat.util import r_dict
from moat.dev import DEV_DIR,DEV

from ..dev import device_types, OnewireDevice

import logging
logger = logging.getLogger(__name__)

__all__ = ['ServerCommand']

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

	async def do(self,args):
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

		try:
			t = await self.root.tree.subdir('bus','onewire',name, create=not self.update)
			await t.subdir('bus')
		except etcd.EtcdAlreadyExist:
			raise CommandError("Host '%s' exists. Use '-u' or choose a different name." % name)
		except etcd.EtcdKeyNotFound:
			raise CommandError("Host '%s' does not exist. Drop '-u' or choose an existing name." % name)
		await t.set('server',{'host':host,'port':port})

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

	async def do(self,args):
		await self.root.setup(self)
		tree = self.root.tree
		if args:
			dirs = args
		else:
			dirs = []
			res = await etc.get('/bus/onewire')
			for r in res.children:
				dirs.append(r.key.rsplit('/',1)[1])
		for d in dirs:
			if self.root.verbose > 1:
				st = await tree.subdir('bus','onewire',d, create=False)
				safe_dump({d: r_dict(dict(st))}, stream=self.stdout)
			elif self.root.verbose:
				hp = await tree.subdir('bus','onewire',d,'server', recursive=True,create=False)
				print(d,hp['host'],hp['port'], sep='\t', file=self.stdout)
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

	async def do(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if not args:
			if not cmd.root.cfg['testing']:
				raise CommandError("You can't delete everything.")
			args = []
			res = etc.get('/bus/onewire')
			for r in res.children:
				args.append(r.name.rsplit('/',1)[1])
		for k in args:
			try:
				await etc.delete('/bus/onewire/'+k, recursive=True)
			except etcd.EtcdKeyNotFound:
				if self.root.verbose:
					print("%s: not known"%k, file=sys.stderr)
			else:
				with suppress(etcd.EtcdKeyNotFound):
					await etc.delete('/task/onewire/'+k, recursive=True)
				with suppress(etcd.EtcdKeyNotFound):
					await etc.delete('/task/moat/scan/bus/onewire/'+k, recursive=True)

class ServerListCommand(Command):
	name = "list"
	summary = "List 1wire servers"
	description = """\
List 1wire servers (OWFS) known to MoaT.

If very verbose, details are shown in YAML format,
otherwise a (short if quiet) list is printed.
"""

	async def do(self,args):
		await self.root.setup(self)
		tree = self.root.tree
		if args:
			dirs = args
		else:
			res = await tree.lookup('bus','onewire')
			dirs = res.keys()
			if self.root.verbose and not dirs:
				print("No servers known.", file=sys.stderr)
		for d in dirs:
			if self.root.verbose > 1:
				st = await tree.subdir('bus','onewire',d, recursive=True)
				safe_dump({d: r_dict(dict(st))}, stream=self.stdout)
			elif self.root.verbose:
				hp = await tree.subdir('bus','onewire',d,'server', recursive=True,create=False)
				print(d,hp['host'],hp['port'], sep='\t', file=self.stdout)
			else:
				print(d, file=self.stdout)

class ServerBusCommand(Command):
	name = "bus"
	summary = "List 1wire buses"
	description = """\
List 1wire buses (OWFS) known to MoaT.
If you name a server and bus, details are shown in YAML format,
else a short list is printed.
"""

	async def do(self,args):
		await self.root.setup(self)
		tree = self.root.tree
		seen = False
		if not args:
			t = await tree.lookup('bus','onewire')
			for srv,v in t.items():
				try:
					v = await v['bus']
				except (etcd.EtcdKeyNotFound,KeyError):
					pass
				else:
					for b in v.keys():
						seen = True
						print(srv,b.replace(' ','/'), sep='\t',file=self.stdout)
			if self.root.verbose and not seen:
				print("No buses known.", file=sys.stderr)
			return
		srv = args.pop(0)
		if not args:
			try:
				t = await tree.subdir('bus','onewire',srv,'bus', create=False,recursive=True)
			except (etcd.EtcdKeyNotFound,KeyError):
				pass
			else:
				for bus,dc in t.items():
					if dc.get('broken',0):
						print(bus,"*inaccessible*", sep='\t',file=self.stdout)
						seen = True
					dc = dc.get('devices',{})
					items = []
					for typ,v in dc.items():
						try:
							dt = device_types()[typ]
							tname = dt.name
						except KeyError:
							dt = OnewireDevice
							tname = '?'+typ
						items.append("%s:%d"%(tname,len(v)))
					print(bus.replace(' ','/'),*items, sep='\t',file=self.stdout)
					seen = True
			if self.root.verbose and not seen:
				print("No buses known.", file=sys.stderr)
			return
		bus = args.pop(0)
		if args:
			raise CommandError("Usage: conn onewire bus [server [bus]]")
		bus = bus.replace('/',' ')
		try:
			t = await tree.subdir('bus','onewire',srv, 'bus',bus,'devices', create=False,recursive=True)
		except (etcd.EtcdKeyNotFound,KeyError):
			raise CommandError("Bus %s:%s does not exist." % (srv,bus))
		for typ,v in t.items():
			try:
				dt = device_types()[typ]
				tname = dt.name
			except KeyError:
				dt = OnewireDevice
				tname = '?'+typ
			for dev in v.keys():
				print(typ+'.'+dev, tname)
				seen = True
		if self.root.verbose and not seen:
			print("No devices known.", file=sys.stderr)

class ServerCommand(SubCommand):
	subCommandClasses = [
		ServerAddCommand,
		ServerListCommand,
		ServerDeleteCommand,
		ServerBusCommand,
	]
	name = "server"
	summary = "OWFS server specific subcommands"
	description = """\
Commands to set up and admin connections to 1wire servers (OWFS).
"""

