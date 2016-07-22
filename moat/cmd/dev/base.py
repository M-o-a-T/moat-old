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
from moat.script import Command, CommandError
from moat.util import r_dict
from moat.dev import DEV_DIR,DEV
from moat.dev.base import Device
from etcd_tree import EtcTypes,EtcInteger
from yaml import safe_dump
import aio_etcd as etcd
import asyncio
import time
import types as py_types
import etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['DeviceListCommand','DeviceLocateCommand','DeviceDescribeCommand']

class DeviceListCommand(Command):
	name = "list"
	summary = "List devices"
	description = """\
List devices found by MoaT.

No arguments: show device classes and counts.
Device class: show those devices.
Device ID: detailed information about the device.
"""

	
	def addOptions(self):
		self.parser.add_option('-r','--recursive',
			action="store_true", dest="recursive",
			help="recurse into subdirectories")

	async def do(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		tree = await self.root._get_tree()
		tree = await tree.subdir(DEV_DIR)
		types = None
		if not args:
			args = ((),)

		if self.options.recursive:
			for arg in args:
				s = [x for x in arg.split('/') if x != '']
				t = await tree.subdir(arg, recursive=False)
				async for dev in t.tagged(DEV):
					self.do_entry(dev)
			return

		for arg in args:
			try:
				res = await tree.subdir(arg, create=False)
			except (etcd.EtcdKeyNotFound, KeyError):
				print("'%s' not found." % (arg,), file=sys.stderr)
			else:
				dev = False
				looped = False
				while len(res) == 1:
					d = list(res.keys())[0]
					if d == DEV:
						break
					looped = True
					res = await res[d]
				for d,rr in res.items():
					rr = await rr
					if d == DEV:
						dev = True
						continue
					print('/'.join(rr.path[len(DEV_DIR):]), len(rr.keys()), sep='\t',file=self.stdout)
				if dev:	
					self.do_entry(res[DEV], not looped)

	def do_entry(self,dev, do_verbose=False):
		path = '/'.join(dev.path[len(DEV_DIR):-1])
		if do_verbose or self.root.verbose > 2:
			safe_dump({path: r_dict(dev)}, stream=self.stdout)
		else:
			print(path, dev.__class__.name, dev.get('location','-'), sep='\t',file=self.stdout)

class _DeviceAttrCommand(Command):
	_attr = None
	_nl = False

	async def do(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		if not args:
			raise CommandError("You need to specify a device.")
		arg = args.pop(0)
		types = EtcTypes()
		Device.types(types)
		try:
			t = await etc.tree((DEV_DIR,arg,(DEV,)), types=types,create=False)
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

class DeviceSignalCommand(Command):
	name = "signal"
	summary = 'set the AMQP signal name for an input or output'

	async def do(self,args):
		await self.root.setup(self)
		etc = self.root.etcd
		path = '/device'
		if not args:
			raise CommandError("You need to specify a device.")
		arg = args.pop(0)
		types = EtcTypes()
		Device.types(types)
		try:
			t = await etc.tree('/'.join((path,arg,DEV)), types=types,create=False)
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

