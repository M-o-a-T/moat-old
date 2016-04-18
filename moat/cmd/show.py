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
from moat.script import Command, SubCommand, CommandError
from etcd_tree.util import from_etcd
import aio_etcd as etcd

import logging
logger = logging.getLogger(__name__)

__all__ = ['ShowCommand']

class ConfigCommand(Command):
	name = "config"
	summary = "View configuration data"""
	description = """\
Show the current config data.

With arguments, show only these.
"""

	async def do(self,args):
		from yaml import safe_dump
		if args:
			try:
				for n,a in enumerate(args):
					if n:
						print("---", file=self.stdout)
					c = self.root.cfg
					for aa in a.split('.'):
						c = c[aa]
					safe_dump(c, stream=self.stdout)
			except KeyError:
				raise CommandError("Key %s does not exist"%(repr(a),))
		else:
			safe_dump(self.root.cfg, stream=self.stdout)

class EtcdCommand(Command):
	name = "etcd"
	summary = "View etcd data"""
	description = """\
Show the current etcd contents.

With arguments, show only these subtrees.
"""

	def addOptions(self):
		self.parser.add_option('-d','--dump',
            action="store_true", dest="dump",
            help="show internal details")
		self.parser.add_option('-m','--modstamp',
            action="store_true", dest="mod",
            help="return the entry's modification number")

	def handleOptions(self):
		self.dump = self.options.dump
		self.mod = self.options.mod

	async def do(self,args):
		from yaml import safe_dump
		retval = 0
		etc = await self.root._get_etcd()
		if args:
			for n,a in enumerate(args):
				if n:
					print("---", file=self.stdout)
				a = a.replace('.','/')
				try:
					if self.mod:
						res = await etc.get('/'+a)
						print(res.modifiedIndex, file=self.stdout)
					else:
						safe_dump(await from_etcd(etc,'/'+a, dump=self.dump), stream=self.stdout)
				except etcd.EtcdKeyNotFound:
					logger.error("key not present: %s",a)
					retval = 1

		else:
			if self.mod:
				res = await etc.get('/')
				print(res.modifiedIndex, file=self.stdout)
			else:
				safe_dump(await from_etcd(etc, '/', dump=self.dump), stream=self.stdout)
		return retval

class DevCommand(Command):
	name = "dev"
	summary = "Update device data"""
	description = """\
Add/Update/Delete device attributes.

Usage: -l path/to                             -- list all devices here
       -s path/to/device                      -- list details for this device
       path/to/device name…                   -- show this value
       path/to/device input                   -- list all inputs
       path/to/device input/name              -- list all values
       path/to/device input/name name…        -- show this value

Of course you can use "output" instead of "input", if the device has any.

"""

	def addOptions(self):
		self.parser.add_option('-d','--dump',
            action="store_true", dest="dump",
            help="show internal details")
		self.parser.add_option('-l','--list',
            action="store_true", dest="list",
            help="Show a list of entries")
		self.parser.add_option('-s','--show',
            action="store_true", dest="show",
            help="Show a single entry")

	async def do(self,args):
		from yaml import safe_dump
		from moat.dev import DEV_DIR,DEV
		from moat.dev.base import _SOURCES
		tree = await self.root._get_tree()
		tree = tree.lookup(DEV_DIR)
		if self.options.list and self.options.show:
			raise CommandError("'-s' and '-l' are mutually exclusive")
		if self.options.list or self.options.show or len(args) < 2:
			if len(args) == 0:
				args = ((),)
			for a in args:
				try:
					t = tree.lookup(a)
					if len(args) == 1 and DEV in t and not self.options.list:
						self.options.show = True
					if self.options.show and DEV not in t:
						print("'%s': not a device.'" % (a,), file=sys.stderr)
						continue
					if not self.options.list and DEV in t:
						d = t['DEV']
						if self.options.dump:
							safe_dump(c, stream=self.stdout)
						else:
							print("device", d.path[len(DEV_DIR):-1], sep='\t',file=self.stdout)
							for k,v in d.items():
								if k in _SOURCES:
									for n,c in v.items():
										print('%s/%s' % (k,n),c.get('value','??'), sep='\t',file=self.stdout)
								else:
									print(k,v, sep='\t',file=self.stdout)
							print("")
					else:
						for d in t.tagged(DEV):
							print('/'.join(d.path[len(DEV_DIR):-1]), sep='\t',file=self.stdout)
				except KeyError:
					print("'%s' does not exist" % (a,), file=sys.stderr)
					continue
		else:
			try:
				t = tree.lookup(args[0],name=DEV)
			except KeyError:
				raise CommandError("Device '%a' not found"%(args[0],))
			else:
				if '/' in args[1]:
					t = t.lookup(args[1])
					if len(args) == 2:
						for k,v in t.items():
							print(k,v.get('value','??'), sep='\t',file=self.stdout)
					else:
						for a in args[1:]:
							try:
								print(a,t[a], sep='\t',file=self.stdout)
							except KeyError:
								print("%s: not found" % (a,), file=sys.stderr)
				elif len(args) == 2 and args[1] in _SOURCES:
					t = t.lookup(args[1])
					for k,v in t.items():
						print(k,v, sep='\t',file=self.stdout)
				else:
					for a in args[1:]:
						try:
							print(a,t[a], sep='\t',file=self.stdout)
						except KeyError:
							print("%s: not found" % (a,), file=sys.stderr)
		



class ShowCommand(SubCommand):
	name = "show"
	summary = "Show various data"""
	description = """\
Show some data.
"""

	subCommandClasses = [EtcdCommand,ConfigCommand,DevCommand]

