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
from moat.dev.onewire import device_types, OnewireDevice
from etcd_tree.util import from_etcd
from etcd_tree.etcd import EtcTypes
from etcd_tree.node import EtcInteger
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
		types.register('server','port',EtcInteger)
		try:
			t = await self.root.etcd.tree('/bus/onewire/'+name, types=types, create=not self.update)
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

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if args:
			dirs = args
		else:
			dirs = []
			res = await etc.get('/bus/onewire')
			for r in res.children:
				dirs.append(r.key.rsplit('/',1)[1])
		for d in dirs:
			if self.root.verbose > 1:
				st = await etc.tree('/bus/onewire/'+d, static=True)
				safe_dump({d: r_dict(dict(st))}, stream=self.stdout)
			elif self.root.verbose:
				h = await etc.get('/bus/onewire/'+d+'/server/host')
				p = await etc.get('/bus/onewire/'+d+'/server/port')
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
			res = etc.get('/bus/onewire')
			for r in res.children:
				args.append(r.name.rsplit('/',1)[1])
		for k in args:
			await etc.delete('/bus/onewire/'+k, recursive=True)
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

class DeviceListCommand(Command):
	name = "list"
	summary = "List 1wire devices"
	description = """\
List 1wire devices (OWFS) found by MoaT.

No arguments: show device classes and counts.
Device class: show those devices.
Device ID: detailed information about the device.
"""

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		path = '/device/onewire'
		if not args:
			res = await etc.get(path)
			for r in res.children:
				typ = r.key[r.key.rindex('/')+1:]
				try:
					dt = device_types()[typ]
				except KeyError:
					dt = '?'+typ
				else:
					dt = dt.name
				rr = await etc.get(path+'/'+typ)
				num = len(list(rr.children))
				print(typ,num,dt, sep='\t',file=self.stdout)
		else:
			types=EtcTypes()

			for arg in args:
				if len(arg) == 2:
					try:
						res = await etc.get(path+'/'+arg)
					except KeyError:
						print("Type '%s' not found." % (arg,), file=sys.stderr)
					else:
						try:
							dt = device_types()[arg]
							tname = dt.name
						except KeyError:
							dt = OnewireDevice
							tname = '?'+arg
						types = EtcTypes()
						dt.types(types)
						for r in res.children:
							dev = r.key[r.key.rindex('/')+1:]
							t = await etc.tree('/'.join((path,arg,dev,':dev')), types=types,static=True,create=False)
							print(arg+'.'+dev,t.get('path','?').replace(' ',':',1).replace(' ','/'),t.get('location','-'), sep='\t',file=self.stdout)

						
				elif '.' in arg:
					typ,dev = arg.split('.',1)
					try:
						dt = device_types()[typ]
						tname = dt.name
					except KeyError:
						dt = OnewireDevice
						tname = '?'+typ
					types = EtcTypes()
					dt.types(types)
					try:
						t = await etc.tree('/'.join((path,typ,dev,':dev')), types=types,static=True,create=False)
					except KeyError:
						print("Device '%s' not found." % (arg,), file=sys.stderr)
					else:
						if self.root.verbose > 1:
							safe_dump({arg: r_dict(t)}, stream=self.stdout)
						else:
							print(arg,tname,t.get('path','?').replace(' ',':',1).replace(' ','/'),t.get('location','-'), sep='\t',file=self.stdout)
				else:
					raise CommandError("'%s' unknown. Please specify either a device class or a device ID."%(arg,))

class DeviceCommand(Command):
	subCommandClasses = [
		DeviceListCommand,
	]
	name = "dev"
	summary = "OWFS device specific subcommands"
	description = """\
Commands to show 1wire bus members
"""

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
			res = await etc.get('/bus/onewire')
			for r in res.children:
				dirs.append(r.key.rsplit('/',1)[1])
		for d in dirs:
			if self.root.verbose > 1:
				st = await etc.tree('/bus/onewire/'+d, static=True)
				safe_dump({d: r_dict(dict(st))}, stream=self.stdout)
			elif self.root.verbose:
				h = await etc.get('/bus/onewire/'+d+'/server/host')
				p = await etc.get('/bus/onewire/'+d+'/server/port')
				print(d,h.value,p.value, sep='\t', file=self.stdout)
			else:
				print(d, file=self.stdout)

class BusListCommand(Command):
	name = "list"
	summary = "List 1wire buses"
	description = """\
List 1wire buses (OWFS) known to MoaT.
If you name a server and bus, details are shown in YAML format,
else a short list is printed.
"""

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if not args:
			t = await etc.tree('/bus/onewire', static=True)
			for srv,v in t.items():
				v = v['bus']
				for b in v.keys():
					print(srv,b.replace(' ','/'), sep='\t',file=self.stdout)
			return
		srv = args.pop(0)
		if not args:
			t = await etc.tree('/bus/onewire/'+srv+'/bus', static=True)
			if int(t.get('broken',0)):
				print(bus,"*inaccessible*", sep='\t',file=self.stdout)
			for bus,dc in t.items():
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
			return
		bus = args.pop()
		if args:
			raise CommandError("Usage: … list [server [bus]]")
		bus = bus.replace('/',' ')
		try:
			t = await etc.tree('/bus/onewire/'+srv+'/bus/'+bus+'/devices', static=True,create=False)
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

class BusCommand(Command):
	subCommandClasses = [
		BusListCommand,
	]
	name = "bus"
	summary = "OWFS bus specific subcommands"
	description = """\
Commands to show 1wire buses
"""


class OneWireCommand(Command):
	name = "1wire"
	summary = "Configure and define tasks"
	description = """\
Commands to set up and admin the task list known to MoaT.
"""

	subCommandClasses = [
		ServerCommand,
		DeviceCommand,
		BusCommand,
	]

