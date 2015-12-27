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
from moat.dev import dev_types
from moat.dev.base import Device
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

__all__ = ['DeviceListCommand','DeviceLocateCommand','DeviceDescribeCommand']

class DeviceListCommand(Command):
	name = "list"
	summary = "List 1wire devices"
	description = """\
List 1wire devices (OWFS) found by MoaT.

No arguments: show device classes and counts.
Device class: show those devices.
Device ID: detailed information about the device.
"""

	
	def addOptions(self):
		self.parser.add_option('-r','--recursive',
			action="store_true", dest="recursive",
			help="recurse into subdirectories")

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		types = None
		path = '/device'
		if not args:
			args = ('',)

		if self.options.recursive:
			types = EtcTypes()
			dev_types(types)
			for arg in args:
				s = [x for x in arg.split('/') if x != '']
				t = await etc.tree(path,sub=s,types=types,static=True)
				for dev in t.tagged(':dev'):
					self.do_entry(dev,dev.path[1:-5])
			return

		for arg in args:
			try:
				if arg == '':
					argp = ()
					arg = path
				else:
					argp = arg.split('/')
					arg = path+'/'+arg
				res = await etc.get(arg)
			except (etcd.EtcdKeyNotFound, KeyError):
				print("'%s' not found." % (arg,), file=sys.stderr)
			else:
				dev = False
				looped = False
				while len(list(res.children)) == 1:
					r = list(res.children)[0]
					d = r.key[r.key.rindex('/')+1:]
					if d == ':dev':
						break
					looped = True
					arg += ('/' if arg else '')+d
					argp.append(d)
					res = await etc.get(arg)
				for r in res.children:
					d = r.key[r.key.rindex('/')+1:]
					if d == ':dev':
						dev = True
						continue
					rr = await etc.get(arg+'/'+d)
					n = 0
					for r in rr.children:
						n += 1
					print(arg+('/' if arg else '')+d,n, sep='\t',file=self.stdout)
				if dev:	
					if types is None:
						types = EtcTypes()
						dev_types(types)
					argp.append(':dev')
					cls = types.lookup(argp, dir=True)
					t = EtcTypes()
					t.register(':dev',cls=cls)
					cls.types(t.step(':dev'))
					t = await etc.tree(arg,sub=':dev', types=t,static=True,create=False)
					self.do_entry(t[':dev'],arg[8:], not looped)

	def do_entry(self,dev,pre='', do_verbose=False):
		if do_verbose or self.root.verbose > 2:
			safe_dump({pre: r_dict(dev)}, stream=self.stdout)
		else:
			print(pre, dev.__class__.name, dev.get('location','-'), sep='\t',file=self.stdout)


class _DeviceAttrCommand(Command):
	_attr = None
	_nl = False

	async def do_async(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		path = '/device'
		if not args:
			raise CommandError("You need to specify an ID.")
		arg = args.pop(0)
		types = EtcTypes()
		Device.types(types)
		try:
			t = await etc.tree('/'.join((path,arg,':dev')), types=types,create=False)
		except KeyError:
			raise CommandError("Device '%s' not found." % (arg,))
		if args:
			args = ' '.join(args)
			if args == '-':
				if self._nl:
					args = sys.stdin.read().rstrip('\n')
				else:
					args = sys.stdin.readline().rstrip('\n')
			await t.set(self._attr,args)
			if self.root.verbose > 1:
				print("Location set.", file=self.stdout)
		elif self._attr in t:
			print(t[self._attr], file=self.stdout)
		elif self.root.verbose:
			print(self._attr.ucfirst()+" not yet set.", file=sys.stderr)
			return 1

class DeviceLocateCommand(_DeviceAttrCommand):
	_attr = 'location'
	name = "locate"
	summary = "Set the location of a device"
	description = """\
Get/Set a device's location.
Usage: … locate ID [text … | -]
         '-' reads the text (one line) from standard input.
"""

class DeviceDescribeCommand(_DeviceAttrCommand):
	_attr = 'description'
	_nl = True
	name = "describe"
	summary = "Set some long-winded description of a device"
	description = """\
Get/Set a device's description.
Usage: … locate ID [text … | -]
         '-' reads the text (multiple lines) from standard input.
"""

