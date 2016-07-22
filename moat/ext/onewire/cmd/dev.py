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

__all__ = ['DeviceCommand']

class DeviceListCommand(Command):
	name = "list"
	summary = "List 1wire devices"
	description = """\
List 1wire devices (OWFS) found by MoaT.

No arguments: show device classes and counts.
Device class: show those devices.
Device ID: detailed information about the device.
"""

	async def do(self,args):
		await self.root.setup(self)
		tree = self.root.tree
		path = DEV_DIR+(OnewireDevice.prefix,)
		if not args:
			res = await tree.lookup(path)
			for r in res.children:
				typ = r.key[r.key.rindex('/')+1:]
				try:
					dt = device_types()[typ]
				except KeyError:
					dt = '?'+typ
				else:
					dt = dt.name
				rr = await tree.subdir(path,name=typ)
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
							t = await etc.tree('/'.join((path,arg,dev,DEV)), types=types,static=True,create=False)
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
						t = await etc.tree('/'.join((path,typ,dev,DEV)), types=types,static=True,create=False)
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

